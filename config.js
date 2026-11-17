// Configuracao publica de runtime da pagina de questao.
// window.SISTEMA_ENEM_API e a URL COMPLETA do endpoint de tentativas.
//
// Atual: Apps Script web app gratuito (Google, conta Marcos Machado de Oliveira),
// /exec publico; tentativas em Google Sheets "Sistema ENEM — tentativas (demo)",
// sem PII (anon_session_id e UUID v4 do navegador); idempotente por client_attempt_id;
// feedback so apos o envio; questao anulada sem alternativa correta.
// Codigo: Apps Script "Sistema ENEM — tentativas (demo)" (projeto guardado no Drive).
//
// Para apontar para o backend FastAPI (backend/api.py): usar a URL COMPLETA
// ".../v1/study/attempts" e trocar o header para application/json nesta pagina.
window.SISTEMA_ENEM_API = "https://script.google.com/macros/s/AKfycby7sGPc83KD0rLQ5b__mdTJQzJRsEIs6nbXq8Aw_2tzeUp9OzBabM6IMXVZvV1nb_Kc/exec";
