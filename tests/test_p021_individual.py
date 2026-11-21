"""Q149 vector alternatives and Q150 logarithm: individual roundtrip smoke."""
from pathlib import Path
from threading import Thread
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parent.parent
class H(SimpleHTTPRequestHandler):
 posts=0
 def log_message(self,*args):pass
 def do_POST(self):H.posts+=1;self.send_error(405)
srv=ThreadingHTTPServer(("127.0.0.1",0),partial(H,directory=str(root)))
Thread(target=srv.serve_forever,daemon=True).start()
checks=[]
def check(name,ok):checks.append(bool(ok));print("PASS" if ok else "FAIL",name,flush=True)
try:
 with sync_playwright() as p:
  b=p.chromium.launch(headless=True)
  pg=b.new_page(viewport={"width":390,"height":844});errors=[]
  pg.on("pageerror",lambda e:errors.append(str(e)))
  home=f"http://127.0.0.1:{srv.server_port}/questao.html?ano=2024&dia=2&pagina=21&caderno=cdamarelo&cor=amarelo"
  pg.goto(home,wait_until="networkidle")
  for idx,n,opt in ((0,149,"B"),(1,150,"E")):
   section=pg.locator(".page-question").nth(idx)
   section.locator(f"input[value={opt}]").check()
   section.locator(".page-question-controls a").click()
   check(f"q{n}_individual_url",f"q{n}" in pg.url)
   check(f"q{n}_draft",pg.locator(f"#alternativas input[value={opt}]").is_checked())
   check(f"q{n}_five_radios",pg.locator("#alternativas input[type=radio]").count()==5)
   if n==149:
    check("q149_vector_alt_images",pg.locator("#alternativas img").evaluate_all("(xs)=>xs.length===5&&xs.every(im=>im.complete&&im.naturalWidth>0)"))
    check("q149_individual_pan_regions",pg.locator("#alternativas .option-individual-pan").count()==5)
    check("q149_individual_scroll",pg.locator("#alternativas .option-individual-pan").evaluate_all("(xs)=>xs.every(x=>x.tabIndex===0&&x.scrollWidth>x.clientWidth+40)"))
    check("q149_caesar_scheme_loaded",pg.locator("#enunciado-estruturado img").evaluate_all("(xs)=>xs.length===1&&xs[0].complete&&xs[0].naturalWidth>1000"))
   else:
    check("q150_richter_equation_loaded",pg.locator("#enunciado-estruturado img").evaluate_all("(xs)=>xs.length===1&&xs[0].complete&&xs[0].naturalWidth>200"))
    check("q150_no_alt_images",pg.locator("#alternativas img").count()==0)
   check(f"q{n}_no_integral_crop",pg.locator("#figura").is_hidden())
   check(f"q{n}_no_external_overflow",pg.evaluate("()=>document.documentElement.scrollWidth<=innerWidth"))
   pg.goto(home,wait_until="networkidle")
  check("q149_q150_drafts_return",pg.locator(".page-question").first.locator("input[value=B]").is_checked() and pg.locator(".page-question").nth(1).locator("input[value=E]").is_checked())
  check("zero_js_errors",not errors)
  b.close()
finally:srv.shutdown()
check("zero_POST",H.posts==0)
print("RESULT",sum(checks),"/",len(checks),flush=True)
assert all(checks)
