import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { resolve, dirname } from "node:path";
import vm from "node:vm";

const base = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const html = readFileSync(resolve(base, "questao.html"), "utf8");
const code = html.match(/<script>\s*([\s\S]*?)<\/script>/)?.[1];
assert.ok(code, "script embutido da página deve existir");

function createHarness(responses, options = {}) {
  const questionId = "enem:2024:regular_nacional:d2:q133";
  const key = "sistema_enem_attempt_" + questionId;
  const localData = options.localData ?? new Map();
  const sessionData = options.sessionData ?? new Map();
  const elements = new Map();
  const posts = [];
  let uuid = 0;

  function element() {
    return {
      hidden: false, className: "", textContent: "", innerHTML: "",
      disabled: false, style: {}, children: [],
      appendChild(node) { this.children.push(node); },
      querySelector(selector) {
        return this.children.find((node) => node?.name &&
          selector.includes('name="' + node.name + '"')) ?? null;
      },
      setAttribute() {},
      addEventListener(type, fn) { this["on_" + type] = fn; },
    };
  }
  const getElement = (id) => {
    if (!elements.has(id)) elements.set(id, element());
    return elements.get(id);
  };
  const option = { value: "A" };
  const confidence = { value: "3" };
  const button = element();
  const document = {
    title: "",
    getElementById: getElement,
    createElement: element,
    createTextNode: (v) => ({ textContent: v }),
    querySelector: (selector) => {
      if (selector === 'input[name="alternativa"]:checked') return option;
      if (selector === 'input[name="confianca"]:checked') return confidence;
      if (selector === '#form-resposta button[type="submit"]') return button;
      return null;
    },
  };
  const store = (map) => ({
    getItem(k) { return map.has(k) ? map.get(k) : null; },
    setItem(k, v) { map.set(k, String(v)); },
    removeItem(k) { map.delete(k); },
  });
  const fetch = async (url, init) => {
    if (url === "catalogo.json") return {
      json: async () => ({ items: [{
        id: "q133", question_id: questionId, numero_oficial: 133,
        ano: 2024, prova: "ENEM", pagina: 15, area: "CN",
        fonte: "INEP", imagem: "q133.png", data: "q133.json",
      }] }),
    };
    if (url === "q133.json") return {
      json: async () => ({ options: [{ label: "A", text: "Opção de teste" }] }),
    };
    posts.push(JSON.parse(init.body));
    if (!responses.length) throw new Error("Sem resposta simulada");
    const next = responses.shift();
    if (next instanceof Error) throw next;
    if (typeof next === "function") return next();
    return {
      ok: next.ok ?? true,
      status: next.status ?? 200,
      json: async () => {
        if (next.invalidJson) throw new SyntaxError("Resposta inválida");
        return next.body;
      },
    };
  };

  const window = { SISTEMA_ENEM_API: "https://example.invalid/exec" };
  vm.runInNewContext(code.replace(/iniciar\(\);\s*$/, "iniciar().catch((err) => { window.__bootstrapError = String(err); });"), {
    window,
    document, location: { search: "?id=q133" }, URLSearchParams,
    fetch,
    sessionStorage: options.noSessionStorage
      ? { getItem() { throw new Error("Indisponível"); },
          setItem() { throw new Error("Indisponível"); },
          removeItem() { throw new Error("Indisponível"); } }
      : store(sessionData),
    localStorage: options.noLocalStorage
      ? { getItem() { throw new Error("Indisponível"); },
          setItem() { throw new Error("Indisponível"); },
          removeItem() { throw new Error("Indisponível"); } }
      : store(localData),
    crypto: { randomUUID: () => "nonce-" + ++uuid },
    Date, Math, Number, String,
  }, { filename: "questao.html" });

  async function ready() {
    // Escoa as microtarefas do contexto vm em uma volta real do event loop.
    await new Promise((resolveTick) => setImmediate(resolveTick));
    assert.equal(typeof getElement("form-resposta").on_submit, "function",
      JSON.stringify({ bootstrapError: window.__bootstrapError, meta: getElement("meta").textContent }));
  }
  async function submit() {
    await ready();
    return getElement("form-resposta").on_submit({ preventDefault() {} });
  }
  return {
    key, posts, localData, sessionData, button, option, confidence, submit, ready,
    selectedControls: () => ({
      alternativas: getElement("alternativas").children
        .map((label) => label.children[0])
        .filter((node) => node?.checked).map((node) => node.value),
      confianca: getElement("confianca").children
        .map((label) => label.children[0])
        .filter((node) => node?.checked).map((node) => node.value),
    }),
    result: () => getElement("resultado"),
  };
}

test("HTTP 200 com erro not_found nao confirma e retém nonce para replay", async () => {
  const h = createHarness([
    { body: { error: "not_found" } },
    { body: { persisted: true, correct: true, official_status: "valid" } },
  ]);
  await h.submit();
  assert.equal(h.posts.length, 1);
  assert.equal(h.result().className, "erro");
  assert.equal(h.sessionData.has(h.key), true);
  const nonce = h.posts[0].client_attempt_id;
  await h.submit();
  assert.equal(h.posts[1].client_attempt_id, nonce);
  assert.equal(h.result().className, "ok");
  assert.match(h.result().textContent, /Correta!/);
  assert.equal(h.sessionData.has(h.key), false);
});

test("JSON malformado conserva identificador e nao exibe feedback", async () => {
  const h = createHarness([{ invalidJson: true }, { body: { persisted: true, correct: false } }]);
  await h.submit();
  assert.equal(h.result().className, "erro");
  assert.equal(h.sessionData.has(h.key), true);
  await h.submit();
  assert.equal(h.posts[0].client_attempt_id, h.posts[1].client_attempt_id);
  assert.match(h.result().textContent, /Incorreta/);
  assert.equal(h.sessionData.has(h.key), false);
});

test("HTTP nao-200 nao consome o nonce de idempotencia", async () => {
  const h = createHarness([{ ok: false, status: 503 }]);
  await h.submit();
  assert.equal(h.posts.length, 1);
  assert.match(h.result().textContent, /503/);
  assert.equal(h.sessionData.has(h.key), true);
});

test("persisted falso, corpo vazio e identidade divergente nao confirmam", async () => {
  for (const body of [
    { persisted: false, correct: true },
    {},
    { persisted: true, error: "conflict", correct: true },
    { persisted: true, question_id: "outra", correct: true },
    { persisted: true, client_attempt_id: "outro", correct: true },
    { persisted: true, ok: false, correct: true },
  ]) {
    const h = createHarness([{ body }]);
    await h.submit();
    assert.equal(h.result().className, "erro", JSON.stringify(body));
    assert.equal(h.sessionData.has(h.key), true, JSON.stringify(body));
  }
});

test("recibo persistido de questao anulada libera nonce e confirma registro", async () => {
  const h = createHarness([{ body: { persisted: true, official_status: "annulled", correct: null } }]);
  await h.submit();
  assert.equal(h.result().className, "ok");
  assert.match(h.result().textContent, /anulada pelo INEP/);
  assert.equal(h.sessionData.has(h.key), false);
});

test("duplo clique enquanto a chamada esta pendente faz apenas um POST", async () => {
  let respond;
  const pending = new Promise((resolvePost) => { respond = resolvePost; });
  const h = createHarness([() => pending]);
  await h.ready();
  const first = h.submit();
  await new Promise((resolveTick) => setImmediate(resolveTick));
  const second = h.submit();
  await new Promise((resolveTick) => setImmediate(resolveTick));
  assert.equal(h.posts.length, 1);
  assert.equal(h.button.disabled, true);
  respond({ ok: true, status: 200, json: async () => ({ persisted: true, correct: true }) });
  await Promise.all([first, second]);
  assert.equal(h.button.disabled, false);
  assert.equal(h.posts.length, 1);
  assert.equal(h.result().className, "ok");
});

test("reenvio com alternativa ou confianca alterada nao reutiliza nonce com payload diferente", async () => {
  const h = createHarness([
    { invalidJson: true },
    { body: { persisted: true, correct: false, official_status: "valid" } },
  ]);
  await h.submit();
  const nonce = h.posts[0].client_attempt_id;
  assert.equal(h.sessionData.has(h.key + "_payload"), true);
  h.option.value = "B";
  await h.submit();
  assert.equal(h.posts.length, 1);
  assert.match(h.result().textContent, /Restaure a seleção anterior/);
  h.option.value = "A";
  h.confidence.value = "4";
  await h.submit();
  assert.equal(h.posts.length, 1);
  h.confidence.value = "3";
  await h.submit();
  assert.equal(h.posts.length, 2);
  assert.equal(h.posts[1].client_attempt_id, nonce);
  assert.equal(h.posts[1].selected_option, "A");
  assert.equal(h.result().className, "ok");
  assert.equal(h.sessionData.has(h.key + "_payload"), false);
});

test("sem armazenamento de sessao nao cria POST com nonce instavel", async () => {
  const h = createHarness([
    { body: { persisted: true, correct: true, official_status: "valid" } },
  ], { noSessionStorage: true });
  await h.submit();
  assert.equal(h.posts.length, 0);
  assert.equal(h.result().className, "erro");
  assert.match(h.result().textContent, /bloqueado para evitar duplicação/);
});

test("resposta nao confirmada nao cria primeira alternativa local; confirmacao cria", async () => {
  const h = createHarness([
    { body: { error: "not_found" } },
    { body: { persisted: true, correct: false, official_status: "valid" } },
  ]);
  const firstKey = "sistema_enem_primeira_enem:2024:regular_nacional:d2:q133";
  await h.submit();
  assert.equal(h.localData.has(firstKey), false);
  assert.equal(h.posts.length, 1);
  await h.submit();
  assert.equal(h.localData.get(firstKey), "A");
});

test("falha no armazenamento da sessao anonima bloqueia POST e nao simula sucesso", async () => {
  const h = createHarness([
    { body: { persisted: true, correct: true } },
  ], { noLocalStorage: true });
  await h.submit();
  assert.equal(h.posts.length, 0);
  assert.equal(h.result().className, "erro");
  assert.match(h.result().textContent, /sessão anônima/);
});

test("recarregamento apos retorno invalido reutiliza nonce e payload idênticos", async () => {
  const localData = new Map();
  const sessionData = new Map();
  const a = createHarness([{ invalidJson: true }], { localData, sessionData });
  await a.submit();
  assert.equal(a.posts.length, 1);
  assert.equal(a.result().className, "erro");
  const original = a.posts[0];
  const b = createHarness([
    { body: { persisted: true, correct: false, official_status: "valid" } },
  ], { localData, sessionData });
  await b.ready();
  assert.deepEqual(b.selectedControls(), { alternativas: ["A"], confianca: ["3"] });
  assert.match(b.result().textContent, /Envio anterior sem confirmação/);
  await b.submit();
  assert.equal(b.posts.length, 1);
  assert.deepEqual(b.posts[0], original);
  assert.equal(b.result().className, "ok");
  assert.equal(sessionData.has(b.key), false);
});

test("sessao anonima alterada nao restaura selecao pendente e nao dispara POST", async () => {
  const localData = new Map(), sessionData = new Map();
  const original = createHarness([{ invalidJson: true }], { localData, sessionData });
  await original.submit();
  localData.set("sistema_enem_anon_session", "sessao-alterada");
  const recovered = createHarness([], { localData, sessionData });
  await recovered.ready();
  assert.deepEqual(recovered.selectedControls(), { alternativas: [], confianca: [] });
  assert.equal(recovered.posts.length, 0);
});
