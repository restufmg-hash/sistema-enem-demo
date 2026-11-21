from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from threading import Thread
from functools import partial
import json
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parent.parent
class Handler(SimpleHTTPRequestHandler):
    posts=0
    def do_POST(self):
        Handler.posts+=1
        self.send_error(405)
    def log_message(self,*args): pass
srv=ThreadingHTTPServer(("127.0.0.1",0),partial(Handler,directory=str(root)))
Thread(target=srv.serve_forever,daemon=True).start()
url=f"http://127.0.0.1:{srv.server_port}/questao.html?ano=2024&dia=2&pagina=14&caderno=cdamarelo&cor=amarelo"
passes=[]
def check(name,condition):
    passes.append((name,bool(condition)))
    print(("PASS" if condition else "FAIL"),name)
try:
 with sync_playwright() as p:
  b=p.chromium.launch(headless=True)
  c=b.new_context(viewport={"width":390,"height":844})
  page=c.new_page();page.goto(url,wait_until="networkidle")
  check("mobile starts reading",page.locator("#page-viewport").evaluate("(e)=>e.classList.contains('read-mode')"))
  check("mobile text size >=16px",page.locator(".page-question p").first.evaluate("(e)=>parseFloat(getComputedStyle(e).fontSize)>=16"))
  check("mobile single column",page.locator(".page-columns").evaluate("(e)=>getComputedStyle(e).gridTemplateColumns.split(' ').length===1"))
  check("mobile readable and no document overflow",page.evaluate("()=>document.documentElement.scrollWidth<=innerWidth"))
  check("toggle aria true",page.locator("#page-reading-mode").get_attribute("aria-pressed")=="true")
  check("zoom disabled when reading",page.locator("#page-zoom-plus").is_disabled())
  page.locator(".page-question").first.locator("input[type=radio][value='B']").check()
  check("question128 B checked",page.locator(".page-question").first.locator("input[type=radio][value='B']").is_checked())
  page.reload(wait_until="networkidle")
  check("draft survives reload",page.locator(".page-question").first.locator("input[type=radio][value='B']").is_checked())
  page.locator("#page-reading-mode").click()
  check("toggle to full two-column mode",not page.locator("#page-viewport").evaluate("(e)=>e.classList.contains('read-mode')"))
  check("zoom controls enabled full",page.locator("#page-zoom-plus").is_enabled())
  check("draft survives reading->full",page.locator(".page-question").first.locator("input[type=radio][value='B']").is_checked())
  page.locator("#page-zoom-plus").click()
  check("zoom operates full",page.locator("#page-status").inner_text().startswith("Zoom"))
  page.locator("#page-reading-mode").click()
  check("return reading with draft",page.locator("#page-viewport").evaluate("(e)=>e.classList.contains('read-mode')") and page.locator(".page-question").first.locator("input[type=radio][value='B']").is_checked())
  check("no POST",Handler.posts==0)
  c.close();b.close()
finally:srv.shutdown()
print("TOTAL",sum(a for _,a in passes),"/",len(passes))
assert all(a for _,a in passes)
