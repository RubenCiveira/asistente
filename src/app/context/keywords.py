class Keywords:
    
    CONTINUE_WRITE_VALID_CHARS = ("/", ":", "#", "@", ".")

    VALID_TRIGGER_PREFIXES = {" ", "\t", "\n", "(", "[", "{", "<"}

    def __init__(self, triggers):
        self._triggers = triggers

    def must_continue(self, txt):
        return str(txt).endswith( self.CONTINUE_WRITE_VALID_CHARS )

    def find_last_trigger(self, before: str) -> tuple[int, int, str | None]:
        trigger_pos = -1
        trigger_len = 0
        trigger_char = None

        for t in self._triggers:
            pos = before.rfind(t)
            if pos == -1:
                continue

            # validar contexto previo
            if pos > 0:
                prev = before[pos - 1]
                if not (prev.isspace() or prev in self.VALID_TRIGGER_PREFIXES):
                    continue

            if pos > trigger_pos:
                trigger_pos = pos
                trigger_len = len(t)
                trigger_char = t

        return trigger_pos, trigger_len, trigger_char