from dataclasses import dataclass

PENDING, ACTIVE, DONE, SKIPPED = "pending", "active", "done", "skipped"

LABELS = {
    "info": "Extrayendo información",
    "video": "Descargando video",
    "audio": "Descargando audio",
    "merge": "Uniendo audio y video",
    "convert": "Convirtiendo",
    "convert_ios": "Convirtiendo para iPhone",
}


@dataclass
class Stage:
    key: str
    label: str
    state: str = PENDING
    pct: float | None = 0.0  # None = en curso sin porcentaje conocido


class StageTracker:
    """Etapas de un job con su propio avance. Se crea al arrancar y vive en memoria."""

    def __init__(self, mode: str):
        keys = ["info", "audio", "convert"] if mode == "audio" else ["info", "video", "audio", "merge"]
        self._stages = {key: Stage(key, LABELS[key]) for key in keys}

    def add(self, key: str) -> None:
        if key not in self._stages:
            self._stages[key] = Stage(key, LABELS[key])

    def begin(self, key: str) -> None:
        stage = self._stages.get(key)
        if stage is None:
            return
        stage.state = ACTIVE
        if key in ("info", "merge", "convert", "convert_ios"):
            stage.pct = None

    def progress(self, key: str, pct: float) -> None:
        stage = self._stages.get(key)
        if stage is None:
            return
        stage.state = ACTIVE
        stage.pct = max(stage.pct or 0.0, min(pct, 99.9))

    def finish(self, key: str) -> None:
        stage = self._stages.get(key)
        if stage is not None and stage.state != SKIPPED:
            stage.state = DONE
            stage.pct = 100.0

    def skip(self, key: str) -> None:
        stage = self._stages.get(key)
        if stage is not None and stage.state in (PENDING, ACTIVE):
            stage.state = SKIPPED
            stage.pct = None

    def settle(self) -> None:
        """Al terminar el job: lo que corría quedó hecho y lo que nunca empezó no aplicó."""
        for stage in self._stages.values():
            if stage.state == ACTIVE:
                stage.state, stage.pct = DONE, 100.0
            elif stage.state == PENDING:
                stage.state, stage.pct = SKIPPED, None

    def snapshot(self) -> list[dict]:
        return [
            {
                "key": s.key,
                "label": s.label,
                "state": s.state,
                "pct": None if s.pct is None else round(s.pct, 1),
            }
            for s in self._stages.values()
        ]
