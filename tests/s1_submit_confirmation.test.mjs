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
  const defaultItem = {
    id: "q133", question_id: questionId, numero_oficial: 133,
    ano: 2024, prova: "ENEM", pagina: 15, area: "CN",
    fonte: "INEP", imagem: "assets/q133.png", data: "data/q133.json",
    occurrence: {
      ano: 2024, dia: 2, caderno: "cdamarelo",
      cor: "amarelo", idioma: null, numero_oficial: 133,
    },
  };
  const fetch = async (url, init) => {
    if (url === "catalogo.json") return {
      json: async () => ({ items: options.catalog ?? [defaultItem] }),
    };
    if (url === "data/q133.json") return {
      json: async () => options.questionData ?? ({
        question_id: questionId,
        options: [..."ABCDE"].map((label) => ({ label, text: "Opção de teste " + label })),
      }),
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
        // O contrato real (v12-v14) sempre vincula a resposta ao envio.
        // rawBody preserva corpos deliberadamente malformados nos testes negativos.
        if (next.body?.persisted === true && !next.rawBody) {
          const last = posts[posts.length - 1];
          return {
            question_id: last.question_id,
            client_attempt_id: last.client_attempt_id,
            attempt_receipt: "123e4567-e89b-12d3-a456-426614174000",
            ...next.body,
          };
        }
        return next.body;
      },
    };
  };

  const window = { SISTEMA_ENEM_API: "https://example.invalid/exec" };
  vm.runInNewContext(code.replace(/iniciar\(\);\s*$/, "iniciar().catch((err) => { window.__bootstrapError = String(err); });"), {
    window,
    document, location: { search: options.search ?? "?id=q133" }, URLSearchParams,
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
    crypto: { randomUUID: () => "nonce-" + String(++uuid).padStart(4, "0") },
    Date, Math, Number, String,
  }, { filename: "questao.html" });

  async function bootstrap() {
    await new Promise((resolveTick) => setImmediate(resolveTick));
    assert.equal(window.__bootstrapError, undefined, "Falha na inicializacao");
  }
  async function ready() {
    // Escoa as microtarefas do contexto vm em uma volta real do event loop.
    await bootstrap();
    assert.equal(typeof getElement("form-resposta").on_submit, "function",
      JSON.stringify({ bootstrapError: window.__bootstrapError, meta: getElement("meta").textContent }));
  }
  async function submit() {
    await ready();
    return getElement("form-resposta").on_submit({ preventDefault() {} });
  }
  return {
    key, posts, localData, sessionData, button, option, confidence, submit, ready, bootstrap,
    meta: () => getElement("meta").textContent,
    formHidden: () => getElement("form-resposta").hidden,
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

test("persisted true sem identidade explicita nao confirma, nem libera nonce", async () => {
  const bodies = [
    { persisted: true, correct: true },
    { persisted: true, question_id: "enem:2024:regular_nacional:d2:q133" },
    { persisted: true, client_attempt_id: "nonce-0002" },
    { persisted: true, question_id: null, client_attempt_id: "nonce-0002" },
    { persisted: true, question_id: "enem:2024:regular_nacional:d2:q133", client_attempt_id: null },
  ];
  for (const body of bodies) {
    const h = createHarness([{ body, rawBody: true }]);
    await h.submit();
    assert.equal(h.posts.length, 1, JSON.stringify(body));
    assert.equal(h.result().className, "erro", JSON.stringify(body));
    assert.equal(h.sessionData.has(h.key), true, JSON.stringify(body));
    assert.equal(h.localData.has("sistema_enem_primeira_enem:2024:regular_nacional:d2:q133"), false);
  }
});

test("persisted true sem recibo opaco do servidor nao confirma", async () => {
  const partial = [
    { persisted: true, correct: true },
    { persisted: true, attempt_receipt: null },
    { persisted: true, attempt_receipt: "" },
    { persisted: true, attempt_receipt: "   " },
    { persisted: true, attempt_receipt: "x" },
    { persisted: true, attempt_receipt: 12345 },
  ];
  for (const body of partial) {
    const h = createHarness([{
      body: {
        question_id: "enem:2024:regular_nacional:d2:q133",
        client_attempt_id: "nonce-0001",
        ...body,
      },
      rawBody: true,
    }]);
    await h.submit();
    assert.equal(h.posts.length, 1, JSON.stringify(body));
    assert.equal(h.result().className, "erro", JSON.stringify(body));
    assert.equal(h.sessionData.has(h.key), true, JSON.stringify(body));
    assert.equal(h.localData.has("sistema_enem_primeira_enem:2024:regular_nacional:d2:q133"), false);
  }
});

test("recibo presente confirma mesmo em replay idempotente", async () => {
  const h = createHarness([{
    body: { persisted: true, replayed: true, correct: false,
            attempt_receipt: "123e4567-e89b-12d3-a456-426614174000" },
  }]);
  await h.submit();
  assert.equal(h.result().className, "ok");
  assert.equal(h.sessionData.has(h.key), false);
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
  respond({ ok: true, status: 200, json: async () => ({
    persisted: true, correct: true,
    question_id: h.posts[0].question_id,
    client_attempt_id: h.posts[0].client_attempt_id,
    attempt_receipt: "123e4567-e89b-12d3-a456-426614174000",
  }) });
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

test("payload pendente sem nonce não cria nova tentativa nem POST", async () => {
  for (const missing of [null, ""]) {
    const key = "sistema_enem_attempt_enem:2024:regular_nacional:d2:q133";
    const storedPayload = JSON.stringify({
      selected_option: "A", confidence: 3,
      anon_session_id: "legacy-safe-session-12345678",
    });
    const sessionData = new Map([[key + "_payload", storedPayload]]);
    if (missing !== null) sessionData.set(key, missing);
    const localData = new Map([
      ["sistema_enem_anon_session", "legacy-safe-session-12345678"],
    ]);
    const h = createHarness([], { sessionData, localData });
    await h.submit();
    assert.equal(h.posts.length, 0, JSON.stringify({ missing }));
    assert.equal(h.result().className, "erro");
    assert.match(h.result().textContent, /envio pendente sem identificador local/);
    assert.equal(sessionData.get(key + "_payload"), storedPayload);
    assert.equal(sessionData.get(key) ?? null, missing);
    assert.equal(localData.has("sistema_enem_primeira_enem:2024:regular_nacional:d2:q133"), false);
  }
});

test("sem nonce e sem payload permanece permitido iniciar tentativa legítima", async () => {
  const sessionData = new Map(), localData = new Map();
  const h = createHarness([{ body: { persisted: true, correct: true } }], {
    sessionData, localData,
  });
  await h.submit();
  assert.equal(h.posts.length, 1);
  assert.equal(h.result().className, "ok");
  assert.equal(sessionData.has(h.key + "_payload"), false);
  assert.equal(sessionData.has(h.key), false);
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


test("filtro numerico invalido nunca e ignorado para escolher outra questao", async () => {
  for (const search of [
    "?ano=abc&numero=133",
    "?ano=0&numero=133",
    "?dia=1.5&numero=133",
    "?numero=abc&ano=2024",
    "?n=-1&ano=2024",
    "?ano=2024x&numero=133",
    "?ano=9007199254740993&numero=133",
    "?ano=&numero=133",
    "?id=q133&ano=abc",
  ]) {
    const h = createHarness([], { search });
    await h.bootstrap();
    assert.equal(h.formHidden(), true, search);
    assert.match(h.meta(), /Filtros de ocorrência inválidos/, search);
    assert.equal(h.posts.length, 0, search);
  }
});

test("duplicidade e conflito em parametros da URL nao escolhem a primeira variante", async () => {
  for (const search of [
    "?ano=2024&ano=2025&numero=133",
    "?numero=133&n=134&ano=2024",
    "?numero=133&n=133&ano=2024",
    "?id=q133&id=q132",
    "?ano=2024&dia=2&dia=1&numero=133",
  ]) {
    const h = createHarness([], { search });
    await h.bootstrap();
    assert.equal(h.formHidden(), true, search);
    assert.match(h.meta(), /duplicados ou conflitantes/, search);
    assert.equal(h.posts.length, 0, search);
  }
});

test("filtros textuais duplicados e identificador vazio nunca escolhem questão", async () => {
  for (const search of [
    "?caderno=cdamarelo&caderno=cdazul&ano=2024&numero=133",
    "?caderno=cdamarelo&caderno=cdamarelo&numero=133",
    "?cor=amarelo&cor=azul&ano=2024&numero=133",
    "?idioma=en&idioma=es&ano=2024&numero=133",
    "?id=&ano=2024&dia=2&numero=133",
    "?id=%20&ano=2024&dia=2&numero=133",
  ]) {
    const h = createHarness([], { search });
    await h.bootstrap();
    assert.equal(h.formHidden(), true, search);
    assert.match(h.meta(), /Filtros de ocorrência inválidos/, search);
    assert.equal(h.posts.length, 0, search);
  }
});

test("consulta valida por numero ou alias n permanece suportada", async () => {
  for (const search of [
    "?ano=2024&dia=2&numero=133",
    "?ano=2024&dia=2&n=133",
    "?id=q133&ano=2024&numero=133",
  ]) {
    const h = createHarness([], { search });
    await h.ready();
    assert.equal(h.formHidden(), false, search);
  }
});

test("id inexistente nao permite fallback silencioso para ocorrencia unica", async () => {
  const h = createHarness([], { search: "?id=ID-INVALIDO&ano=2024&dia=2&numero=133" });
  await h.bootstrap();
  assert.match(h.meta(), /Identificador de questão não encontrado/);
  assert.equal(h.formHidden(), true);
  assert.equal(h.posts.length, 0);
});

test("id existente com filtros contraditorios nao seleciona outra questao", async () => {
  const h = createHarness([], { search: "?id=q133&ano=2025&dia=2&numero=133" });
  await h.bootstrap();
  assert.match(h.meta(), /não correspondem à mesma questão/);
  assert.equal(h.formHidden(), true);
  assert.equal(h.posts.length, 0);
});

test("sem id e sem filtros nao exibe a primeira questao arbitrariamente", async () => {
  const h = createHarness([], { search: "" });
  await h.bootstrap();
  assert.match(h.meta(), /Informe o identificador ou os filtros/);
  assert.equal(h.formHidden(), true);
  assert.equal(h.posts.length, 0);
});

test("fallback por ocorrencia unica permanece valido na ausencia de id", async () => {
  const h = createHarness([], { search: "?ano=2024&dia=2&caderno=cdamarelo&numero=133" });
  await h.ready();
  assert.equal(h.formHidden(), false);
  assert.equal(h.posts.length, 0);
});

test("id correto e filtros consistentes permanecem validos", async () => {
  const h = createHarness([], { search: "?id=q133&ano=2024&dia=2&numero=133" });
  await h.ready();
  assert.equal(h.formHidden(), false);
});

test("id direto duplicado nao seleciona arbitrariamente a primeira ocorrencia", async () => {
  const standard = {
    id: "q133", question_id: "enem:2024:regular_nacional:d2:q133",
    numero_oficial: 133, ano: 2024, prova: "ENEM",
    pagina: 15, area: "CN", fonte: "INEP", imagem: "assets/q133.png", data: "data/q133.json",
    occurrence: { ano: 2024, dia: 2, caderno: "cdamarelo", numero_oficial: 133 },
  };
  const duplicate = {
    ...standard,
    question_id: "enem:2025:regular_nacional:d2:q133",
    occurrence: { ano: 2025, dia: 2, caderno: "cdamarelo", numero_oficial: 133 },
  };
  const h = createHarness([], { search: "?id=q133", catalog: [standard, duplicate] });
  await h.bootstrap();
  assert.equal(h.formHidden(), true);
  assert.equal(h.posts.length, 0);
});

test("arquivo de alternativas nao pode pertencer a outra questao", async () => {
  const h = createHarness([], {
    questionData: {
      question_id: "enem:2024:regular_nacional:d2:q132",
      options: [..."ABCDE"].map((label) => ({ label, text: "Teste" })),
    },
  });
  await h.bootstrap();
  assert.equal(h.formHidden(), true);
  assert.match(h.meta(), /Alternativas incompatíveis/);
  assert.equal(h.posts.length, 0);
});

test("arquivo de alternativas sem identidade nao libera formulario", async () => {
  const h = createHarness([], {
    questionData: { options: [..."ABCDE"].map((label) => ({ label, text: "Teste" })) },
  });
  await h.bootstrap();
  assert.equal(h.formHidden(), true);
  assert.equal(h.posts.length, 0);
});

test("alternativas duplicadas, ausentes ou com rotulo invalido nao liberam envio", async () => {
  const variations = ["AABDE", "ABCD", "ABCDF"];
  for (const labels of variations) {
    const h = createHarness([], {
      questionData: {
        question_id: "enem:2024:regular_nacional:d2:q133",
        options: [...labels].map((label) => ({ label, text: "Teste" })),
      },
    });
    await h.bootstrap();
    assert.equal(h.formHidden(), true, labels);
    assert.match(h.meta(), /Alternativas incompatíveis/, labels);
    assert.equal(h.posts.length, 0, labels);
  }
});

test("alternativas validas e identidade correta permitem formulario", async () => {
  const h = createHarness([]);
  await h.ready();
  assert.equal(h.formHidden(), false);
});

test("referencias externas de alternativas e imagem bloqueiam formulario sem POST", async () => {
  for (const corrupt of [
    { data: "https://example.invalid/questao.json" },
    { imagem: "https://example.invalid/questao.png" },
    { imagem_texto: "https://example.invalid/base.png" },
  ]) {
    const item = {
      id: "q133", question_id: "enem:2024:regular_nacional:d2:q133",
      numero_oficial: 133, ano: 2024, prova: "ENEM", pagina: 15,
      area: "CN", fonte: "INEP", imagem: "assets/q133.png", data: "data/q133.json",
      ...corrupt,
    };
    const h = createHarness([], { catalog: [item] });
    await h.bootstrap();
    assert.equal(h.formHidden(), true, JSON.stringify(corrupt));
    assert.match(h.meta(), /Referências de arquivos/, JSON.stringify(corrupt));
    assert.equal(h.posts.length, 0);
  }
});

test("travessia de diretórios e query strings nos recursos não liberam envio", async () => {
  for (const corrupt of [
    { data: "data/../private.json" },
    { data: "data/q133.json?token=1" },
    { imagem: "assets/../outside.png" },
    { imagem_texto: "//example.invalid/path.png" },
  ]) {
    const item = {
      id: "q133", question_id: "enem:2024:regular_nacional:d2:q133",
      numero_oficial: 133, ano: 2024, prova: "ENEM", pagina: 15,
      area: "CN", fonte: "INEP", imagem: "assets/q133.png", data: "data/q133.json",
      ...corrupt,
    };
    const h = createHarness([], { catalog: [item] });
    await h.bootstrap();
    assert.equal(h.formHidden(), true, JSON.stringify(corrupt));
    assert.match(h.meta(), /Referências de arquivos/, JSON.stringify(corrupt));
    assert.equal(h.posts.length, 0);
  }
});

test("caminhos de recursos locais esperados continuam funcionando", async () => {
  const h = createHarness([]);
  await h.ready();
  assert.equal(h.formHidden(), false);
});

test("IDs recém-gerados respeitam as restrições da candidata privada v15", async () => {
  const h = createHarness([{ body: { persisted: true, correct: false } }]);
  await h.submit();
  assert.equal(h.posts.length, 1);
  const body = h.posts[0];
  assert.match(body.client_attempt_id, /^[A-Za-z0-9][A-Za-z0-9_-]{7,79}$/);
  assert.match(body.anon_session_id, /^[A-Za-z0-9][A-Za-z0-9_-]{7,127}$/);
  assert.equal(h.result().className, "ok");
});

test("sessão anônima preexistente inválida impede POST sem alterar dados", async () => {
  for (const invalid of [
    "curta", "=HYPERLINK(foo)", "sessao.com.pontos", "A".repeat(129),
  ]) {
    const localData = new Map([["sistema_enem_anon_session", invalid]]);
    const h = createHarness([], { localData });
    await h.submit();
    assert.equal(h.posts.length, 0, invalid);
    assert.equal(h.result().className, "erro", invalid);
    assert.equal(localData.get("sistema_enem_anon_session"), invalid);
    assert.equal(localData.has("sistema_enem_primeira_enem:2024:regular_nacional:d2:q133"), false);
  }
});

test("nonce local corrompido impede POST e mantém a tentativa pendente intacta", async () => {
  for (const invalid of ["curto", "=IMPORTXML(foo)", "x".repeat(81), "A/B"]) {
    const sessionData = new Map();
    const key = "sistema_enem_attempt_enem:2024:regular_nacional:d2:q133";
    const payloadKey = key + "_payload";
    sessionData.set(key, invalid);
    sessionData.set(payloadKey, "TESTE_PENDENTE_PRESERVADO");
    const h = createHarness([], { sessionData });
    await h.submit();
    assert.equal(h.posts.length, 0, invalid);
    assert.equal(h.result().className, "erro", invalid);
    assert.match(h.result().textContent, /Identificador de tentativa local inválido/);
    assert.equal(sessionData.get(key), invalid);
    assert.equal(sessionData.get(payloadKey), "TESTE_PENDENTE_PRESERVADO");
  }
});

test("identificadores válidos anteriormente armazenados seguem idempotentes", async () => {
  const sessionData = new Map();
  const localData = new Map();
  const id = "legacy-safe-id-123456789";
  const sid = "legacy-safe-session-123456789";
  const key = "sistema_enem_attempt_enem:2024:regular_nacional:d2:q133";
  sessionData.set(key, id);
  localData.set("sistema_enem_anon_session", sid);
  const h = createHarness([{ body: { persisted: true, correct: false } }], {
    sessionData, localData,
  });
  await h.submit();
  assert.equal(h.posts.length, 1);
  assert.equal(h.posts[0].client_attempt_id, id);
  assert.equal(h.posts[0].anon_session_id, sid);
  assert.equal(h.result().className, "ok");
});
