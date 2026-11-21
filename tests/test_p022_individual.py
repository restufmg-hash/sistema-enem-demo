from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from threading import Thread
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parent.parent
class H(SimpleHTTPRequestHandler):
 posts=0
 def log_message(self,*a):pass
 def do_POST(self):H.posts+=1;self.send_error(405)
srv=ThreadingHTTPServer(("127.0.0.1",0),partial(H,directory=str(root)))
Thread(target=srv.serve_forever,daemon=True).start()
checks=[]
def ck(k,v):checks.append(bool(v));print("PASS" if v else "FAIL",k,flush=True)
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True)
  pg=browser.new_page(viewport={"width":390,"height":844});errors=[]
  pg.on("pageerror",lambda e:errors.append(str(e)))
  home=f"http://127.0.0.1:{srv.server_port}/questao.html?ano=2024&dia=2&pagina=22&caderno=cdamarelo&cor=amarelo"
  pg.goto(home,wait_until="networkidle")
  for i,n,letter in ((0,151,"B"),(1,152,"D")):
   sect=pg.locator(".page-question").nth(i)
   sect.locator(f"input[value={letter}]").check()
   sect.locator(".page-question-controls a").click()
   ck(f"q{n}_url",f"q{n}" in pg.url)
   ck(f"q{n}_selected",pg.locator(f"#alternativas input[value={letter}]").is_checked())
   ck(f"q{n}_five_radios",pg.locator("#alternativas input[type=radio]").count()==5)
   ck(f"q{n}_original_image",pg.locator("#enunciado-estruturado img").evaluate_all("(xs)=>xs.length===1&&xs[0].complete&&xs[0].naturalWidth>900"))
   if n==151:
    ck("q151_five_vector_images",pg.locator("#alternativas img").evaluate_all("(xs)=>xs.length===5&&xs.every(x=>x.complete&&x.naturalWidth>0)"))
   else:
    ck("q152_text_alternatives",pg.locator("#alternativas img").count()==0)
   ck(f"q{n}_no_full_crop",pg.locator("#figura").is_hidden())
   ck(f"q{n}_no_overflow",pg.evaluate("()=>document.documentElement.scrollWidth<=innerWidth"))
   pg.goto(home,wait_until="networkidle")
  ck("drafts_roundtrip",pg.locator(".page-question").first.locator("input[value=B]").is_checked() and pg.locator(".page-question").nth(1).locator("input[value=D]").is_checked())
  ck("zero_errors",not errors)
  browser.close()
finally:srv.shutdown()
ck("zero_POST",H.posts==0)
print("RESULT",sum(checks),"/",len(checks),flush=True)
assert all(checks)
