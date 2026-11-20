from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from threading import Thread
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parent.parent
class Handler(SimpleHTTPRequestHandler):
 posts=0
 def do_POST(self):
  Handler.posts+=1;self.send_error(405)
 def log_message(self,*args):pass
srv=ThreadingHTTPServer(("127.0.0.1",0),partial(Handler,directory=str(root)))
Thread(target=srv.serve_forever,daemon=True).start()
checks=[]
def test(label,condition):
 checks.append(bool(condition));print(("PASS" if condition else "FAIL"),label)
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True)
  for width,mode in [(1365,"desktop"),(390,"mobile")]:
   c=browser.new_context(viewport={"width":width,"height":844})
   page=c.new_page();errors=[]
   page.on("pageerror",lambda e:errors.append(str(e)))
   page.goto(f"http://127.0.0.1:{srv.server_port}/questao.html?ano=2024&dia=2&pagina=11&caderno=cdamarelo&cor=amarelo",wait_until="networkidle")
   options=["B","C","D"]
   sections=page.locator(".page-question")
   for i,opt in enumerate(options):
    sections.nth(i).locator(f"input[type=radio][value={opt}]").check()
   test(mode+"_three_selections",all(sections.nth(i).locator(f"input[type=radio][value={opt}]").is_checked() for i,opt in enumerate(options)))
   page.reload(wait_until="networkidle")
   sections=page.locator(".page-question")
   test(mode+"_reload_recovers",all(sections.nth(i).locator(f"input[type=radio][value={opt}]").is_checked() for i,opt in enumerate(options)))
   for n in (119,120,121):
    section=page.locator(".page-question").nth(n-119)
    link=section.locator(".page-question-controls a")
    test(mode+f"_link_{n}",link.count()==1 and f"q{n}" in link.get_attribute("href"))
   page.locator(".page-question").nth(1).locator(".page-question-controls a").click()
   test(mode+"_question120_link_navigates","q120" in page.url)
   test(mode+"_question120_draft",page.locator("input[type=radio][value=C]").first.is_checked())
   test(mode+"_no_uncaught_js",not errors)
   c.close()
  browser.close()
finally:srv.shutdown()
test("zero_POST",Handler.posts==0)
print("RESULT",sum(checks),"/",len(checks))
assert all(checks)
