from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from threading import Thread
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parent.parent
class Handler(SimpleHTTPRequestHandler):
 def log_message(self,*args): pass
server=ThreadingHTTPServer(("127.0.0.1",0),partial(Handler,directory=str(root)))
Thread(target=server.serve_forever,daemon=True).start()
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True)
  for width,mode in [(1365,"desktop"),(390,"mobile")]:
   context=browser.new_context(viewport={"width":width,"height":844})
   page=context.new_page();errors=[]
   page.on("pageerror",lambda e:errors.append(str(e)))
   response=page.goto(f"http://127.0.0.1:{server.server_port}/questao.html?ano=2024&dia=2&pagina=13&caderno=cdamarelo&cor=amarelo",wait_until="networkidle")
   titles=page.locator(".page-question h2").all_inner_texts()
   imgs=page.locator("#page-sheet img").count()
   readable=page.locator("#page-viewport").evaluate("(e)=>e.classList.contains('read-mode')")
   no_overflow=page.evaluate("()=>document.documentElement.scrollWidth<=innerWidth")
   print(mode,"HTTP",response.status,"titles",titles,"images",imgs,"read",readable,"overflow",not no_overflow,"errors",errors)
   assert response.status==200 and titles==[f"QUESTÃO {i}" for i in range(124,128)]
   assert imgs==3 and not errors and no_overflow
   if mode=="mobile": assert readable
   context.close()
  browser.close()
finally:server.shutdown()
print("P13_REGRESSION_PASS")
