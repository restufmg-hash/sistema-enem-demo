"""Q146 modo individual: imagens e rascunhos, sem envio."""
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
def check(n,value):
 checks.append(bool(value));print("PASS" if value else "FAIL",n,flush=True)
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True)
  pg=browser.new_page(viewport={"width":390,"height":844});errors=[]
  pg.on("pageerror",lambda e:errors.append(str(e)))
  home=f"http://127.0.0.1:{srv.server_port}/questao.html?ano=2024&dia=2&pagina=19&caderno=cdamarelo&cor=amarelo"
  pg.goto(home,wait_until="networkidle")
  pg.locator(".page-graphic-options input[value=D]").check()
  pg.locator(".page-question-controls a").click()
  check("q146_individual_url","q146" in pg.url)
  check("q146_draft_D",pg.locator("#alternativas input[value=D]").is_checked())
  check("q146_five_radios",pg.locator("#alternativas input[type=radio]").count()==5)
  check("q146_five_original_pngs",pg.locator("#alternativas img").evaluate_all("(xs)=>xs.length===5 && xs.every(x=>x.complete&&x.naturalHeight===600&&[960,975].includes(x.naturalWidth))"))
  check("q146_image_alt_labels",pg.locator("#alternativas img").evaluate_all("(xs)=>xs.every((x,i)=>x.alt.includes('ABCDE'[i]))"))
  check("q146_no_integral_crop",pg.locator("#figura").is_hidden())
  check("q146_no_stimulus_image",pg.locator("#enunciado-estruturado img").count()==0)
  pg.goto(home,wait_until="networkidle")
  check("q146_roundtrip_D",pg.locator(".page-graphic-options input[value=D]").is_checked())
  check("q146_no_errors",not errors)
  browser.close()
finally:srv.shutdown()
check("zero_POST",H.posts==0)
print("RESULT",sum(checks),"/",len(checks),flush=True)
assert all(checks)
