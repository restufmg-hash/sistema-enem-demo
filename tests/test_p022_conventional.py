from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from threading import Thread
from playwright.sync_api import sync_playwright
import json,hashlib,argparse,pymupdf
root=Path(__file__).resolve().parent.parent
a=argparse.ArgumentParser();a.add_argument("--pdf",type=Path,required=True);args=a.parse_args()
l=json.loads((root/"data/enem2024_d2_cdamarelo_p022_layout.json").read_text(encoding="utf8"))
assert [x["number"] for x in l["questions"]]==[151,152] and l["layout"]["mode"]=="two_column"
assert l["source"]["printed_page"]==22 and l["source"]["pdf_page_index"]==21
assert len(l["media"])==7 and len(l["response_targets"])==10
assert hashlib.sha256(args.pdf.read_bytes()).hexdigest()==l["source"]["sha256"]
doc=pymupdf.open(str(args.pdf));page=doc[21];words=page.get_text("words")
for t in l["response_targets"]:
 assert len([w for w in words if w[4]==t["label"] and abs(w[0]-t["bbox"][0])<.08 and abs(w[1]-t["bbox"][1])<.08])==1,t
for key,m in l["media"].items():
 assert hashlib.sha256((root/m["url"]).read_bytes()).hexdigest()==m["sha256"],key
 if m["source_kind"]=="native_image":
  assert hashlib.sha256(doc.extract_image(m["source_xref"])["image"]).hexdigest()==m["sha256"]
 else:
  blob=page.get_pixmap(matrix=pymupdf.Matrix(3,3),clip=pymupdf.Rect(m["source_bbox"]),alpha=False).tobytes("png")
  assert hashlib.sha256(blob).hexdigest()==m["sha256"],key
q151=json.loads((root/l["questions"][0]["source_data"]).read_text(encoding="utf8"))
q152=json.loads((root/l["questions"][1]["source_data"]).read_text(encoding="utf8"))
assert [x["label"] for x in q151["options"]]==list("ABCDE")
assert all(x["image_only"] and x["asset"]==l["media"]["q151-"+x["label"]]["url"] for x in q151["options"])
assert [x["text"] for x in q152["options"]]==["7.","8.","9.","10.","11."]
assert sum(b["type"]=="image" for b in q151["blocks"])==1 and sum(b["type"]=="image" for b in q152["blocks"])==1
print("SOURCE_PASS SHA PDF 10_LABELS 2_NATIVE 5_VECTOR_CROPS",flush=True)
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
  b=pw.chromium.launch(headless=True)
  for width,mode in ((1365,"desktop"),(390,"mobile")):
   ctx=b.new_context(viewport={"width":width,"height":844});p=ctx.new_page();errors=[]
   p.on("pageerror",lambda e:errors.append(str(e)))
   resp=p.goto(f"http://127.0.0.1:{srv.server_port}/questao.html?ano=2024&dia=2&pagina=22&caderno=cdamarelo&cor=amarelo",wait_until="networkidle")
   ck(mode+"_200",resp.status==200)
   ck(mode+"_questions",p.locator(".page-question h2").all_inner_texts()==["QUESTÃO 151","QUESTÃO 152"])
   ck(mode+"_columns",p.locator(".page-columns .page-column").count()==2)
   ck(mode+"_radios",p.locator(".page-question input[type=radio]").count()==10)
   ck(mode+"_five_math",p.locator(".page-question").first.locator(".page-q-option.visual img").count()==5)
   ck(mode+"_originals",all(p.locator(".page-question").nth(i).locator("figure img").count()==1 for i in (0,1)))
   ck(mode+"_seven_loaded",p.locator(".page-question img").evaluate_all("(xs)=>xs.length===7&&xs.every(x=>x.complete&&x.naturalWidth>0)"))
   ck(mode+"_no_overflow",p.evaluate("()=>document.documentElement.scrollWidth<=innerWidth"))
   if mode=="mobile":
    ck("mobile_read_mode",p.locator("#page-viewport.read-mode").count()==1)
    ck("mobile_graphs_fit",p.locator(".page-q-option.visual img").evaluate_all("(xs)=>xs.length===5&&xs.every(x=>{let a=x.getBoundingClientRect(),b=x.closest('label').getBoundingClientRect();return a.right<=b.right+1&&a.width>40;})"))
   for i,v in ((0,"B"),(1,"D")):p.locator(".page-question").nth(i).locator(f"input[value={v}]").check()
   p.reload(wait_until="networkidle")
   ck(mode+"_drafts",p.locator(".page-question").first.locator("input[value=B]").is_checked() and p.locator(".page-question").nth(1).locator("input[value=D]").is_checked())
   ck(mode+"_js",not errors)
   image=root/f"p022_renderer_{mode}.png";p.screenshot(path=str(image),full_page=True)
   print("CAPTURE_SHA",mode,hashlib.sha256(image.read_bytes()).hexdigest(),flush=True)
   ctx.close()
  b.close()
finally:srv.shutdown()
ck("zero_POST",H.posts==0)
print("RESULT",sum(checks),"/",len(checks),flush=True)
assert all(checks)
