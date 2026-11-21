"""Q157-Q160: individual question navigation and draft continuity."""
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
def ck(n,ok):checks.append(bool(ok));print("PASS" if ok else "FAIL",n,flush=True)
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch(headless=True)
  pg=b.new_page(viewport={"width":390,"height":844});errs=[]
  pg.on("pageerror",lambda e:errs.append(str(e)))
  home=f"http://127.0.0.1:{srv.server_port}/questao.html?ano=2024&dia=2&pagina=25&caderno=cdamarelo&cor=amarelo"
  pg.goto(home,wait_until="networkidle")
  for idx,n,letter in ((0,157,"A"),(1,158,"B"),(2,159,"C"),(3,160,"D")):
   section=pg.locator(".page-question").nth(idx)
   section.locator(f"input[value={letter}]").check()
   section.locator(".page-question-controls a").click()
   ck(f"q{n}_url",f"q{n}" in pg.url)
   ck(f"q{n}_draft",pg.locator(f"#alternativas input[value={letter}]").is_checked())
   ck(f"q{n}_five_options",pg.locator("#alternativas input[type=radio]").count()==5)
   if n==158:
    ck("q158_five_math_images",pg.locator("#alternativas img").evaluate_all("(xs)=>xs.length===5&&xs.every(x=>x.complete&&x.naturalWidth>0)"))
    ck("q158_no_stimulus_image",pg.locator("#enunciado-estruturado img").count()==0)
   elif n==159:
    ck("q159_native_poster",pg.locator("#enunciado-estruturado img").evaluate_all("(xs)=>xs.length===1&&xs[0].complete&&xs[0].naturalWidth===1006"))
    ck("q159_no_option_images",pg.locator("#alternativas img").count()==0)
   else:
    ck(f"q{n}_text_only",pg.locator("#alternativas img").count()==0 and pg.locator("#enunciado-estruturado img").count()==0)
   ck(f"q{n}_no_full_crop",pg.locator("#figura").is_hidden())
   ck(f"q{n}_no_overflow",pg.evaluate("()=>document.documentElement.scrollWidth<=innerWidth"))
   pg.goto(home,wait_until="networkidle")
  ck("all_four_roundtrip",all(pg.locator(".page-question").nth(i).locator(f"input[value={l}]").is_checked() for i,l in enumerate("ABCD")))
  ck("no_javascript_errors",not errs)
  b.close()
finally:srv.shutdown()
ck("zero_POST",H.posts==0)
print("RESULT",sum(checks),"/",len(checks),flush=True)
assert all(checks)
