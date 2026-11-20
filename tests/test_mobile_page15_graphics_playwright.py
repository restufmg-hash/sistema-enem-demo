from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parent.parent
class Handler(SimpleHTTPRequestHandler):
 posts=0
 def log_message(self,*args):pass
 def do_POST(self):
  Handler.posts+=1;self.send_error(405)
server=ThreadingHTTPServer(("127.0.0.1",0),partial(Handler,directory=str(root)))
Thread(target=server.serve_forever,daemon=True).start()
checks=[]
def check(label,passed):
 checks.append(bool(passed));print(("PASS" if passed else "FAIL"),label)
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True)
  for width,mode in ((1365,"desktop"),(390,"mobile")):
   context=browser.new_context(viewport={"width":width,"height":844})
   page=context.new_page();errors=[]
   page.on("pageerror",lambda err:errors.append(str(err)))
   response=page.goto(f"http://127.0.0.1:{server.server_port}/questao.html?ano=2024&dia=2&pagina=15&caderno=cdamarelo&cor=amarelo",wait_until="networkidle")
   check(mode+"_200",response.status==200)
   check(mode+"_q133_135",page.locator(".page-question h2").all_inner_texts()==["QUESTÃO 133","QUESTÃO 134","QUESTÃO 135"])
   check(mode+"_options",page.locator(".page-question input[type=radio]").count()==15)
   assets=page.locator("#page-sheet img").evaluate_all("(xs)=>xs.map(x=>({src:x.getAttribute('src'),ok:x.complete&&x.naturalWidth>0}))")
   check(mode+"_seven_loaded_graphics",len(assets)==7 and all(x["ok"] for x in assets))
   check(mode+"_five_heredograms",sum("q135_option_" in x["src"] for x in assets)==5)
   check(mode+"_no_js_error",not errors)
   check(mode+"_no_document_overflow",page.evaluate("()=>document.documentElement.scrollWidth<=innerWidth"))
   check(mode+"_responsive",page.locator("#page-viewport").evaluate("(el)=>el.classList.contains('read-mode')")==(mode=="mobile"))
   if mode=="mobile":
    check("mobile_text_readable",page.locator(".page-question p").first.evaluate("(el)=>parseFloat(getComputedStyle(el).fontSize)>=16"))
    q135=page.locator(".page-question").last
    check("mobile_q135_options_graphics",q135.locator("input[type=radio]").count()==5 and q135.locator("img").count()==6)
    q135.locator("input[type=radio][value='C']").check()
    page.reload(wait_until="networkidle")
    check("mobile_q135_draft_reload",page.locator(".page-question").last.locator("input[type=radio][value='C']").is_checked())
   context.close()
  browser.close()
finally:server.shutdown()
check("zero_post",Handler.posts==0)
print("RESULT",sum(checks),"/",len(checks))
assert all(checks)
