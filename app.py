import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import atexit

    import marimo as mo
    import plotly.express as px
    import polars as pl

    from daq import DAQController, SourceKind, scan_daq_sources

    MAX_SAMPLES = 10_000

    return (
        DAQController,
        MAX_SAMPLES,
        SourceKind,
        atexit,
        mo,
        pl,
        px,
        scan_daq_sources,
    )


@app.cell
def _(DAQController, MAX_SAMPLES, atexit):
    controller = DAQController(max_samples=MAX_SAMPLES)

    # Assigning to _ prevents the returned function from rendering as an output expression
    _ = atexit.register(controller.close)

    return (controller,)


@app.cell
def _(mo):
    rescan_button = mo.ui.button(
        label="Ports neu scannen",
        value=0,
        on_click=lambda count: count + 1,
        kind="neutral",
    )
    start_button = mo.ui.run_button(
        label="START",
        kind="success",
    )
    stop_button = mo.ui.run_button(
        label="STOP",
        kind="danger",
    )
    display_refresh = mo.ui.refresh(
        options=["500ms", "1s", "2s"],
        default_interval="500ms",
        label="Anzeigeintervall",
    )
    return display_refresh, rescan_button, start_button, stop_button


@app.cell
def _(mo, rescan_button, scan_daq_sources):
    _scan_generation = rescan_button.value
    _sources = scan_daq_sources()
    source_by_id = {source.source_id: source for source in _sources}
    source_options = {source.label: source.source_id for source in _sources}
    _default_label = next(iter(source_options)) if source_options else None
    source_dropdown = mo.ui.dropdown(
        options=source_options,
        value=_default_label,
        label="DAQ-Quelle",
        full_width=True,
    )
    return source_by_id, source_dropdown


@app.cell
def _(
    controller,
    source_by_id,
    source_dropdown,
    start_button,
    stop_button,
):
    _selected_source = source_by_id.get(source_dropdown.value)
    action_message = ""
    try:
        if _selected_source:
            action_message = controller.select_source(_selected_source)
        if stop_button.value:
            action_message = controller.stop()
        elif start_button.value:
            action_message = controller.start()
    except (ConnectionError, OSError, RuntimeError, ValueError) as _exc:
        action_message = f"Fehler: {_exc}"
    return (action_message,)


@app.cell
def _(action_message, controller, display_refresh, pl):
    _refresh_tick = display_refresh.value
    _action_dependency = action_message
    state = controller.status_snapshot()
    _rows = controller.snapshot()

    if _rows:
        data = pl.DataFrame(
            _rows,
            schema=[("time_ms", pl.Int64), ("value", pl.Int64)],
            orient="row",
        ).with_columns(
            (
                (pl.col("time_ms") - pl.col("time_ms").first()) / 1000.0
            ).alias("elapsed_s")
        )
    else:
        data = pl.DataFrame(
            schema={
                "time_ms": pl.Int64,
                "value": pl.Int64,
                "elapsed_s": pl.Float64,
            }
        )
    return data, state


@app.cell
def _(
    MAX_SAMPLES,
    SourceKind,
    action_message,
    display_refresh,
    mo,
    rescan_button,
    source_by_id,
    source_dropdown,
    start_button,
    state,
    stop_button,
):
    _pico_count = sum(
        source.kind is SourceKind.PICO for source in source_by_id.values()
    )

    _kind_map = {
        "hardware": "success",
        "simulation": "warn",
        "error": "danger",
        "idle": "neutral",
    }
    _callout_kind = _kind_map.get(state["mode"], "neutral")

    _status_msg = (
        f"**Status:** {state['text']} | "
        f"Puffer: {state['samples']:,}/{MAX_SAMPLES:,} Samples"
    )
    if action_message:
        _status_msg += f" ({action_message})"
    if state["error"]:
        _status_msg += f"\n\nHinweis: {state['error']}"

    control_card = mo.md(
        f"""
        # 📊 Messwerterfassung
        Gefundene Pico/RP2040-Boards: **{_pico_count}** *(Simulator ist immer verfügbar)*
        """
    )

    status_card = mo.callout(mo.md(_status_msg), kind=_callout_kind)

    controls_layout = mo.vstack(
        [
            control_card,
            mo.hstack(
                [source_dropdown, rescan_button],
                align="end",
                widths=[3, 1],
            ),
            mo.hstack(
                [start_button, stop_button, display_refresh],
                justify="start",
            ),
            status_card,
        ],
        gap=1,
    )
    return (controls_layout,)


@app.cell
def _(data, mo, px, state):
    if state["running"] or data.height:
        _title = (
            f"Live-Messwerte ({data.height:,} Samples)"
            if state["running"]
            else f"Messwerte ({data.height:,} Samples)"
        )
        figure = px.line(
            data,
            x="elapsed_s",
            y="value",
            title=_title,
            labels={
                "elapsed_s": "Verstrichene Zeit [s]",
                "value": "Messwert",
            },
        )
        figure.update_layout(template="plotly_white", uirevision="keep-zoom")
        chart_element = mo.ui.plotly(figure)
    else:
        chart_element = mo.callout(
            mo.md("Noch keine abgeschlossene Messung vorhanden."),
            kind="neutral",
        )
    return (chart_element,)


@app.cell
def _(chart_element, controls_layout, mo):
    mo.vstack(
        [
            controls_layout,
            mo.md("---"),
            chart_element,
        ]
    )
    return


if __name__ == "__main__":
    app.run()
