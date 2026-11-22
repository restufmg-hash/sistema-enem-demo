"""Smoke de navegador isolado da PR S1. Nunca acessa Apps Script real.

Execute fora do Codespaces, com Playwright Python/Chromium disponíveis:
    python tests/test_s1_attempt_browser.py
Todas as chamadas externas são abortadas; o endpoint de tentativas é simulado.
"""
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
assert (ROOT / "questao.html").is_file(), "questao.html ausente"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


catalog = {"items": [{
    "id": "q133",
    "question_id": "enem:2024:regular_nacional:d2:q133",
    "numero_oficial": 133,
    "ano": 2024,
    # Metadado hostil somente de QA: jamais deve virar HTML executavel.
    "prova": 'ENEM <img src="data:,invalid" onerror="window.__catalogXssTriggered=true">',
    "pagina": 15,
    "area": "CN",
    "fonte": "INEP",
    "imagem": "assets/imagem-ficticia.png",
    "data": "data/q133.json",
    "occurrence": {
        "ano": 2024, "dia": 2, "caderno": "cdamarelo",
        "cor": "amarelo", "idioma": None, "numero_oficial": 133,
    },
}]}
alternativas = {
    "question_id": "enem:2024:regular_nacional:d2:q133",
    "options": [
        {"label": letter, "text": "Alternativa ficticia " + letter}
        for letter in "ABCDE"
    ],
}
question_id = catalog["items"][0]["question_id"]
nonce_key = "sistema_enem_attempt_" + question_id
first_key = "sistema_enem_primeira_" + question_id


def test_viewport(browser, url, viewport):
    posts, errors, external = [], [], []
    context = browser.new_context(viewport=viewport)
    page = context.new_page()
    page.on("pageerror", lambda exc: errors.append(str(exc)))

    def allow_local(route):
        if route.request.url.startswith(url + "/"):
            route.continue_()
        else:
            external.append(route.request.url)
            route.abort()

    # Fail closed: no actual external traffic, including the production Apps Script.
    page.route("**/*", allow_local)
    page.route("**/config.js", lambda route: route.fulfill(
        content_type="text/javascript",
        body='window.SISTEMA_ENEM_API = "https://example.invalid/exec";',
    ))
    page.route("**/catalogo.json", lambda route: route.fulfill(json=catalog))
    page.route("**/data/q133.json", lambda route: route.fulfill(json=alternativas))

    def fake_post(route):
        assert route.request.method == "POST"
        payload = json.loads(route.request.post_data)
        posts.append(payload)
        body = (
            {"error": "not_found"}
            if len(posts) == 1
            else {
                "persisted": True, "correct": False, "official_status": "valid",
                "question_id": payload["question_id"],
                "client_attempt_id": payload["client_attempt_id"],
            }
        )
        route.fulfill(json=body)

    page.route("https://example.invalid/exec", fake_post)

    try:
        page.goto(url + "/questao.html?id=q133", wait_until="networkidle")
        # O metadado perigoso deve aparecer como texto, nao como imagem/script.
        assert page.locator("#meta img, #meta svg, #meta script").count() == 0
        assert page.evaluate("window.__catalogXssTriggered === true") is False
        assert "<img src=" in page.locator("#meta").inner_text()
        page.locator('input[name="alternativa"][value="A"]').check()
        page.locator('input[name="confianca"][value="3"]').check()
        page.locator('button[type="submit"]').click()
        page.get_by_text("Não foi possível confirmar a gravação", exact=False).wait_for()
        assert len(posts) == 1, posts
        first_nonce = posts[0]["client_attempt_id"]
        state = page.evaluate(
            "([nonce, first]) => ({nonce: sessionStorage.getItem(nonce), "
            "first: localStorage.getItem(first)})", [nonce_key, first_key]
        )
        assert state == {"nonce": first_nonce, "first": None}, state

        # Alterar a alternativa não pode repetir o mesmo nonce com conteúdo novo.
        page.locator('input[name="alternativa"][value="B"]').check()
        page.locator('button[type="submit"]').click()
        page.get_by_text("Restaure a seleção anterior", exact=False).wait_for()
        assert len(posts) == 1, posts

        # Novo carregamento no mesmo contexto mantém nonce, sessão e payload.
        page.reload(wait_until="networkidle")
        assert page.locator('input[name="alternativa"][value="A"]').is_checked()
        assert page.locator('input[name="confianca"][value="3"]').is_checked()
        page.get_by_text("Envio anterior sem confirmação", exact=False).wait_for()
        assert len(posts) == 1, "Reload nao deve iniciar POST"
        page.locator('button[type="submit"]').click()
        page.get_by_text("Resposta registrada no servidor. Incorreta.", exact=True).wait_for()
        assert len(posts) == 2 and posts[1] == posts[0], posts
        final = page.evaluate(
            "([nonce, first]) => ({nonce: sessionStorage.getItem(nonce), "
            "first: localStorage.getItem(first)})", [nonce_key, first_key]
        )
        assert final == {"nonce": None, "first": "A"}, final

        # Identidade explicita desconhecida: nunca selecionar outra questao.
        page.goto(
            url + "/questao.html?id=inexistente&ano=2024&dia=2&numero=133",
            wait_until="networkidle",
        )
        page.get_by_text("Identificador de questão não encontrado", exact=False).wait_for()
        assert page.locator("#form-resposta").is_hidden()
        assert len(posts) == 2

        # Identidade conhecida com filtros contraditorios: negar o formulario.
        page.goto(url + "/questao.html?id=q133&ano=2025&numero=133", wait_until="networkidle")
        page.get_by_text("não correspondem à mesma questão", exact=False).wait_for()
        assert page.locator("#form-resposta").is_hidden()
        assert len(posts) == 2

        # Ausencia de ambos os filtros e id: sem escolha arbitraria.
        page.goto(url + "/questao.html", wait_until="networkidle")
        page.get_by_text("Informe o identificador ou os filtros", exact=False).wait_for()
        assert page.locator("#form-resposta").is_hidden()

        # Fallback sem id permanece possivel se a ocorrencia for inequivoca.
        page.goto(
            url + "/questao.html?ano=2024&dia=2&caderno=cdamarelo&numero=133",
            wait_until="networkidle",
        )
        page.locator('input[name="alternativa"][value="A"]').wait_for()
        assert page.locator("#form-resposta").is_visible()
        assert len(posts) == 2

        # Resposta local alterada jamais pode misturar alternativas de outro ID.
        page.unroute("**/data/q133.json")
        data_mock = {
            "question_id": "enem:2024:regular_nacional:d2:q132",
            "options": alternativas["options"],
        }
        page.route("**/data/q133.json", lambda route: route.fulfill(json=data_mock))
        page.goto(url + "/questao.html?id=q133", wait_until="networkidle")
        page.get_by_text("Alternativas incompatíveis", exact=False).wait_for()
        assert page.locator("#form-resposta").is_hidden()
        assert len(posts) == 2

        # Mesmo ID, mas alternativas repetidas: nao habilitar submissao.
        data_mock = {
            "question_id": question_id,
            "options": [
                {"label": letter, "text": "Alternativa ficticia"}
                for letter in "AABDE"
            ],
        }
        page.goto(url + "/questao.html?id=q133", wait_until="networkidle")
        page.get_by_text("Alternativas incompatíveis", exact=False).wait_for()
        assert page.locator("#form-resposta").is_hidden()
        assert len(posts) == 2

        # Nao permitir fetch remoto indicado por metadados do catalogo.
        page.unroute("**/catalogo.json")
        outside_catalog = {"items": [{
            **catalog["items"][0],
            "data": "https://example.invalid/private.json",
        }]}
        page.route("**/catalogo.json", lambda route: route.fulfill(json=outside_catalog))
        page.goto(url + "/questao.html?id=q133", wait_until="networkidle")
        page.get_by_text("Referências de arquivos", exact=False).wait_for()
        assert page.locator("#form-resposta").is_hidden()
        assert len(posts) == 2

        assert not errors, errors
        assert not external, external  # No unrecognized / real network calls.
        print(
            "S1_BROWSER_PASS",
            f"viewport={viewport['width']}x{viewport['height']}",
            "HTTP200_ERROR_BLOCKED",
            "RETRY_NONCE_STABLE",
            "FIRST_ANSWER_AFTER_CONFIRMATION",
            "EXPLICIT_ID_FAIL_CLOSED",
            "OPTIONS_IDENTITY_FAIL_CLOSED",
            "EXTERNAL_RESOURCE_FAIL_CLOSED",
            "EXTERNAL_REQUESTS=0",
            "JS_ERRORS=0",
        )
    finally:
        context.close()


def main():
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT))
    )
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    url = "http://127.0.0.1:" + str(server.server_address[1])
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                for viewport in [
                    {"width": 390, "height": 844},
                    {"width": 1280, "height": 800},
                ]:
                    test_viewport(browser, url, viewport)
            finally:
                browser.close()
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
