// Código do Google Apps Script que envia os e-mails do Louvor IPO.
// Colar em https://script.google.com (logado no Gmail remetente) e publicar como App da Web.
// Definir a propriedade de script SECRET com o mesmo valor de APPS_SCRIPT_EMAIL_SECRET do Railway.

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var secret = PropertiesService.getScriptProperties().getProperty('SECRET');

    if (!secret || data.secret !== secret) {
      return resposta({ ok: false, error: 'unauthorized' });
    }

    var opcoes = { name: 'Louvor IPO' };
    if (data.htmlBody) opcoes.htmlBody = data.htmlBody;

    MailApp.sendEmail(data.to, data.subject, data.body, opcoes);
    return resposta({ ok: true });
  } catch (err) {
    return resposta({ ok: false, error: String(err) });
  }
}

function resposta(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

// Rode esta função uma vez pelo editor para autorizar o envio de e-mails.
function testarEnvio() {
  MailApp.sendEmail(Session.getActiveUser().getEmail(), 'Teste Louvor IPO', 'Funcionou!');
}
