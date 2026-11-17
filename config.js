// Configuracao publica de runtime da pagina de questao.
// Vazio = jornada de tentativa indisponivel (a pagina informa com honestidade).
// Para habilitar POST + feedback real, apontar para uma instancia publicada da
// API de demonstracao (backend/api.py) com persistencia ligada via
// ENEM_ATTEMPT_STORE=<caminho sqlite> no host, por exemplo:
// window.SISTEMA_ENEM_API = "https://SEU-HOST-AQUI";
// O host nunca expoe gabarito antes do envio; a conferencia acontece no servidor.
window.SISTEMA_ENEM_API = "";
