"""ENEM 2024 D2 C5 p023 Q153: origin and browser checks."""
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from threading import Thread
import argparse,hashlib,json,pymupdf
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parent.parent
a=argparse.ArgumentParser();a.add_argument("--pdf",type=Path,required=True);args=a.parse_args()
layout=json.loads((root/"data/enem2024_d2_cdamarelo_p023_layout.json").read_text(encoding="utf8"))
qid="enem:2024:regular_nacional:d2:q153"
assert layout["layout"]["mode"]=="single_question_graphics"
assert len(layout["questions"])==1 and layout["questions"][0]["number"]==153
assert layout["source"]["printed_page"]==23 and layout["source"]["pdf_page_index"]==22
assert len(layout["media"])==6 and len(layout["response_targets"])==5
q=json.loads((root/layout["questions"][0]["source_data"]).read_text(encoding="utf8"))
assert q["question_id"]==qid and [v["label"] for v in q["options"]]==list("ABCDE")
assert len(q["blocks"])==4 and len([v for v in q["blocks"] if v["type"]=="image"])==1
assert all(v["image_only"] and v["asset"]==layout["media"]["q153-"+v["label"]]["url"] for v in q["options"])
assert hashlib.sha256(args.pdf.read_bytes()).hexdigest()==layout["source"]["sha256"]
pdf=pymupdf.open(str(args.pdf));assert len(pdf)==32
page=pdf[22];words=page.get_text("words")
for x in layout["response_targets"]:
 assert len([w for w in words if w[4]==x["label"] and abs(w[0]-x["bbox"][0])<.08 and abs(w[1]-x["bbox"][1])<.08])==1,x
for label,xref in zip("ABCDE",(242,244,246,248,250)):
 entry=layout["media"]["q153-"+label];original=pdf.extract_image(xref)
 assert entry["source_xref"]==xref
 assert entry["sha256"]==hashlib.sha256(original["image"]).hexdigest()
 assert hashlib.sha256((root/entry["url"]).read_bytes()).hexdigest()==entry["sha256"]
 assert all(abs(x-y)<.01 for x,y in zip(entry["source_bbox"],list(page.get_image_rects(xref)[0])))
tank=layout["media"]["q153-tank"];assert tank["source_xref"]==240
assert tank["sha256"]==hashlib.sha256(pdf.extract_image(240)["image"]).hexdigest()
assert hashlib.sha256((root/tank["url"]).read_bytes()).hexdigest()==tank["sha256"]
assert not any(v["source_xref"]==368 for v in layout["media"].values())
print("SOURCE_PASS 5_NATIVE_GRAPHS 5_OPTION_COORDINATES PDF_SHA",flush=True)
class H(SimpleHTTPRequestHandler):
 posts=0
 def log_message(self,*a):pass
 def do_POST(self):H.posts+=1;self.send_error(405)
server=ThreadingHTTPServer(("127.0.0.1",0),partial(H,directory=str(root)))
Thread(target=server.serve_forever,daemon=True).start()
passes=[]
def check(name,ok):
 passes.append(bool(ok));print("PASS" if ok else "FAIL",name,flush=True)
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True)
  for width,mode in ((1365,"desktop"),(390,"mobile")):
   context=browser.new_context(viewport={"width":width,"height":844})
   pg=context.new_page();errs=[]
   pg.on("pageerror",lambda err:errs.append(str(err)))
   response=pg.goto(f"http://127.0.0.1:{server.server_port}/questao.html?ano=2024&dia=2&pagina=19&caderno=cdamarelo&cor=amarelo",wait_until="networkidle")
   check(mode+"_200",response.status==200)
   check(mode+"_one_question",pg.locator(".page-question h2").all_inner_texts()==["QUESTÃO 153"])
   check(mode+"_one_column",pg.locator(".page-columns.single-question-graphics .page-column").count()==1)
   check(mode+"_five_options",pg.locator(".page-graphic-options input[type=radio]").count()==5)
   images=pg.locator(".page-graphic-options img").evaluate_all("(xs)=>xs.map(x=>({w:x.naturalWidth,h:x.naturalHeight,ok:x.complete&&x.naturalWidth>0}))")
   check(mode+"_five_native_images",len(images)==5 and all(i["ok"] and i["h"]==574 and i["w"]==733 for i in images))
   check(mode+"_original_tank",pg.locator(".page-question figure img").evaluate_all("(xs)=>xs.length===1&&xs[0].complete&&xs[0].naturalWidth===696&&xs[0].naturalHeight===320"))
   check(mode+"_labels_order",pg.locator(".page-graphic-options label").evaluate_all("(xs)=>xs.map(x=>x.dataset.optionLabel).join('')")=="ABCDE")
   check(mode+"_zero_external_overflow",pg.evaluate("()=>document.documentElement.scrollWidth<=innerWidth"))
   if mode=="mobile" and pg.locator("#page-reading-mode").count():
    check("mobile_read_mode_active",pg.locator("#page-viewport.read-mode").count()==1)
    check("mobile_graphics_inside_labels",pg.locator(".page-graphic-options img").evaluate_all("(xs)=>xs.every(i=>{const a=i.getBoundingClientRect(),p=i.closest('label').getBoundingClientRect();return a.left>=p.left&&a.right<=p.right+1&&a.width>70;})"))
    rows=pg.locator(".page-graphic-options label").evaluate_all("(xs)=>xs.map(x=>x.getBoundingClientRect().y)")
    check("mobile_A_to_E_vertical",all(x<y for x,y in zip(rows,rows[1:])))
   elif mode=="desktop":
    xy=pg.locator(".page-graphic-options label").evaluate_all("(xs)=>xs.map(x=>({l:x.getBoundingClientRect().left,t:x.getBoundingClientRect().top}))")
    check("desktop_ABC_left_DE_right",len(xy)==5 and all(abs(xy[i]["l"]-xy[0]["l"])<2 for i in (1,2)) and abs(xy[3]["l"]-xy[4]["l"])<2 and xy[3]["l"]>xy[0]["l"])
    check("desktop_two_columns_order",xy[0]["t"]<xy[1]["t"]<xy[2]["t"] and abs(xy[3]["t"]-xy[0]["t"])<2)
   pg.locator(".page-graphic-options input[value=C]").check()
   pg.reload(wait_until="networkidle")
   check(mode+"_draft_recovered",pg.locator(".page-graphic-options input[value=C]").is_checked())
   check(mode+"_individual_link",pg.locator(".page-question-controls a").count()==1)
   check(mode+"_no_js_errors",not errs)
   f=root/f"p023_renderer_{mode}.png"
   pg.screenshot(path=str(f),full_page=True)
   print("CAPTURE_SHA",mode,hashlib.sha256(f.read_bytes()).hexdigest(),flush=True)
   context.close()
  browser.close()
finally:server.shutdown()
check("zero_POST",H.posts==0)
print("RESULT",sum(passes),"/",len(passes),flush=True)
assert all(passes)
