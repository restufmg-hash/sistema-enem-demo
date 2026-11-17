// Configuracao publica de runtime da pagina de questao.
// window.SISTEMA_ENEM_API aponta para a API de tentativas publicada.
//
// ATENCAO: host ATUAL e um codespace publico de DEMONSTRACAO
// (anonimo, sem PII, tentativas em sqlite efemero no codespace; some junto
// com o ambiente). Pendente de hospedagem gratuita duradoura (Supabase/
// Apps Script/Vercel). Ao ficar indisponivel, a pagina informa honestamente
// que o envio ao servidor falhou e guarda a resposta no navegador.
// Backend: backend/api.py do repo sistema-enem (endpoints /v1/study/*),
// com ENEM_ATTEMPT_STORE para persistencia SQLite e idempotencia por
// client_attempt_id. Never set any secret here.
window.SISTEMA_ENEM_API = "https://fluffy-space-zebra-gxpvq5pg97v93pwg-8000.app.github.dev";
