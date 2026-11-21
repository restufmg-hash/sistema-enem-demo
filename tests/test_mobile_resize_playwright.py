from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from threading import Thread
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parent.parent
class Handler(SimpleHTTPRequestHandler):
 def log_message(self,*a): pass
 def do_POST(self):
  raise AssertionError("No answer submission expected")
srv=ThreadingHTTPServer(("127.0.0.1",0),partial(Handler,directory=str(root)))
Thread(target=srv.serve_forever,daemon=True).start()
url=f"http://127.0.0.1:{srv.server_port}/questao.html?ano=2024&dia=2&pagina=14&caderno=cdamarelo&cor=amarelo"
checks=[]
def check(title,yes):
 checks.append(bool(yes));print(("PASS" if yes else "FAIL"),title)
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True)
  context=browser.new_context(viewport={"width":390,"height":844})
  page=context.new_page()
  errors=[];page.on("pageerror",lambda err:errors.append(str(err)))
  page.goto(url,wait_until="networkidle")
  read=lambda:page.locator("#page-viewport").evaluate("(e)=>e.classList.contains('read-mode')")
  check("initial mobile read",read())
  page.locator(".page-question").first.locator("input[value=B]").check()
  page.set_viewport_size({"width":1024,"height":768})
  page.wait_for_function("() => !document.querySelector('#page-viewport').classList.contains('read-mode')",timeout=3500)
  check("automatic desktop full",not read())
  check("desktop fit adjusts",page.locator("#page-status").inner_text().startswith("Zoom"))
  page.set_viewport_size({"width":390,"height":844})
  page.wait_for_function("() => document.querySelector('#page-viewport').classList.contains('read-mode')",timeout=3500)
  check("auto return mobile read",read())
  check("preserves selected option",page.locator(".page-question").first.locator("input[value=B]").is_checked())
  page.locator("#page-reading-mode").click()
  page.set_viewport_size({"width":1024,"height":768})
  page.set_viewport_size({"width":390,"height":844})
  check("manual full respected on resize",not read())
  page.locator("#page-reading-mode").click()
  page.set_viewport_size({"width":1024,"height":768})
  check("manual reading respected on resize",read())
  check("text remains readable",page.locator(".page-question p").first.evaluate("(el)=>parseFloat(getComputedStyle(el).fontSize)>=16"))
  check("no JS exceptions",not errors)
  check("no document overflow",page.evaluate("()=>document.documentElement.scrollWidth<=innerWidth"))
  context.close();browser.close()
finally:srv.shutdown()
print("RESULT",sum(checks),"/",len(checks))
assert all(checks)
