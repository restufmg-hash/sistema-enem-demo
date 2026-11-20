from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from threading import Thread
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parent.parent
class Handler(SimpleHTTPRequestHandler):
 posts=0
 def do_POST(self):
  Handler.posts+=1;self.send_error(405)
 def log_message(self,*args):pass
server=ThreadingHTTPServer(("127.0.0.1",0),partial(Handler,directory=str(root)))
Thread(target=server.serve_forever,daemon=True).start()
url=f"http://127.0.0.1:{server.server_port}/questao.html?ano=2024&dia=2&pagina=12&caderno=cdamarelo&cor=amarelo"
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
   response=page.goto(url,wait_until="networkidle")
   check(mode+"_http200",response.status==200)
   titles=page.locator(".page-question h2").all_inner_texts()
   check(mode+"_unique_questions",titles==["QUESTÃO 122","QUESTÃO 123"])
   check(mode+"_one_continuation",page.locator(".page-question-continued").count()==1)
   check(mode+"_column_layout",page.locator(".page-column").count()==2)
   check(mode+"_ten_selectable",page.locator("#page-sheet input[type=radio]").count()==10)
   check(mode+"_options_in_right_continuation",page.locator(".page-question-continued input[type=radio]").count()==5)
   check(mode+"_other_options_separate",page.locator(".page-question").last.locator("input[type=radio]").count()==5)
   check(mode+"_three_diagrams",page.locator("#page-sheet img").count()==3 and page.locator("#page-sheet img").evaluate_all("(xs)=>xs.every(x=>x.complete&&x.naturalWidth>0)"))
   check(mode+"_no_integral_crop",page.locator("#page-sheet img").evaluate_all("(xs)=>xs.every(x=>!x.src.includes('integral'))"))
   check(mode+"_no_scroll_overflow",page.evaluate("()=>document.documentElement.scrollWidth<=innerWidth"))
   check(mode+"_reading_mode",page.locator("#page-viewport").evaluate("(x)=>x.classList.contains('read-mode')")==(mode=="mobile"))
   q122=page.locator(".page-question-continued")
   q123=page.locator(".page-question").last
   q122.locator("input[value=B]").check()
   q123.locator("input[value=D]").check()
   check(mode+"_two_drafts_separate",q122.locator("input[value=B]").is_checked() and q123.locator("input[value=D]").is_checked())
   page.reload(wait_until="networkidle")
   q122=page.locator(".page-question-continued")
   q123=page.locator(".page-question").last
   check(mode+"_drafts_survive_reload",q122.locator("input[value=B]").is_checked() and q123.locator("input[value=D]").is_checked())
   q122.locator(".page-question-controls a").click()
   check(mode+"_question_link",page.url.find("id=enem2024-d2-cdamarelo-q122")>=0)
   check(mode+"_question_draft",page.locator("input[type=radio][value=B]").first.is_checked())
   check(mode+"_no_page_errors",not errors)
   context.close()
  browser.close()
finally:server.shutdown()
check("zero_post",Handler.posts==0)
print("RESULT",sum(checks),"/",len(checks))
assert all(checks)
