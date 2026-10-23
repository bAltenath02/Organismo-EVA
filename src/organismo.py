"""Ponto de entrada mínimo da EVA."""

from memoria import ErroDeMemoria, Memoria


def iniciar() -> Memoria:
    memoria = Memoria.carregar_ou_criar()
    memoria.registrar_evento("inicio", {"primeira_inicializacao": memoria.primeira_inicializacao})
    return memoria


if __name__ == "__main__":
    try:
        memoria = iniciar()
    except ErroDeMemoria as erro:
        print(f"EVA não iniciou com segurança: {erro}")
        raise SystemExit(1)

    print("EVA iniciou.")
    print(f"Experiências registradas: {len(memoria.estado['experiencias'])}.")
