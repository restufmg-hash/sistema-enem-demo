from pathlib import Path
from threading import Thread
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parent.parent
class H(SimpleHTTPRequestHandler):
 posts=0
 def log_message(self,*a):pass
 def do_POST(self):H.posts+=1;self.send_error(405)
srv=ThreadingHTTPServer(("127.0.0.1",0),partial(H,directory=str(root)))
Thread(target=srv.serve_forever,daemon=True).start()
checks=[]
def check(label,ok):
 checks.append(bool(ok));print("PASS" if ok else "FAIL",label)
try:
 with sync_playwright() as p:
  b=p.chromium.launch(headless=True)
  context=b.new_context(viewport={"width":390,"height":844})
  page=context.new_page();errors=[]
  page.on("pageerror",lambda e:errors.append(str(e)))
  page.goto(f"http://127.0.0.1:{srv.server_port}/questao.html?ano=2024&dia=2&pagina=17&caderno=cdamarelo&cor=amarelo",wait_until="networkidle")
  for n in (140,141,142):
   source=page.locator(".page-question").nth(n-140)
   source.locator("input[value=B]").check()
   source.locator(".page-question-controls a").click()
   check(f"q{n}_individual_url",f"q{n}" in page.url)
   check(f"q{n}_draft",page.locator("#alternativas input[value=B]").is_checked())
   check(f"q{n}_options",page.locator("#alternativas input").count()==5)
   if n==141:
    check("q141_five_fraction_images",page.locator("#alternativas img").count()==5 and page.locator("#alternativas img").evaluate_all("(xs)=>xs.every(x=>x.complete&&x.naturalWidth>0)"))
    check("q141_no_stimulus_image",page.locator("#enunciado-estruturado img").count()==0)
   if n==142:
    check("q142_phones_image_loaded",page.locator("#enunciado-estruturado img").count()==1 and page.locator("#enunciado-estruturado img").first.evaluate("(im)=>im.complete&&im.naturalWidth===840"))

   check(f"q{n}_no_integral_crop",page.locator("#figura").is_hidden())
   page.goto(f"http://127.0.0.1:{srv.server_port}/questao.html?ano=2024&dia=2&pagina=17&caderno=cdamarelo&cor=amarelo",wait_until="networkidle")
  check("no_page_errors",not errors)
  context.close();b.close()
finally:srv.shutdown()
check("no_post",H.posts==0)
print("RESULT",sum(checks),"/",len(checks))
assert all(checks)
