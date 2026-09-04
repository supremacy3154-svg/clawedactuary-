#!/usr/bin/env python3
"""Generate an A4 research-note .docx for the Tesla Cybercab memo (not site HTML)."""
from __future__ import annotations

import argparse
import smtplib
import ssl
import sys
from email import encoders
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from smtp_config import FROM_ADDR, PASSWORD, SMTP_HOST, SMTP_PORT, USERNAME

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "personal-site" / "images" / "2026-09-04-tesla-cybercab-motor-vehicle-insurance"
OUT_DIR = ROOT / "data" / "reports"
OUT_NAME = "2026-09-04-Tesla-Cybercab-机动车身份与保险监管口径-研究报告.docx"

NAVY = RGBColor(0x1F, 0x4E, 0x79)
INK = RGBColor(0x1A, 0x18, 0x14)
MUTED = RGBColor(0x5A, 0x57, 0x50)
RULE = "1F4E79"
BODY_SIZE = 12
EAST = "宋体"
EAST_HEAD = "黑体"


def set_run_font(run, *, east: str = EAST, size: Pt | None = None, bold: bool | None = None, color=None):
    if size is not None:
        run.font.size = size
    if bold is not None:
        run.bold = bold
    if color is not None:
        run.font.color.rgb = color
    run.font.name = "Times New Roman"
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), "Times New Roman")
    rFonts.set(qn("w:hAnsi"), "Times New Roman")
    rFonts.set(qn("w:eastAsia"), east)


def shade_cell(cell, hex_color: str) -> None:
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), hex_color)
    shd.set(qn("w:val"), "clear")
    tcPr.append(shd)


def set_cell_border(cell) -> None:
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:color"), "8FAADC")
        tcBorders.append(el)
    tcPr.append(tcBorders)


def add_bottom_border(paragraph, color: str = RULE, sz: str = "12") -> None:
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), sz)
    bottom.set(qn("w:space"), "8")
    bottom.set(qn("w:color"), color)
    pBdr.append(bottom)
    pPr.append(pBdr)


def set_paragraph_spacing(p, *, before=0, after=8, line=22, first_line=None):
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = Pt(line)
    if first_line is not None:
        pf.first_line_indent = Cm(first_line)


def add_body(doc, text: str, *, first_line=0.74):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    set_paragraph_spacing(p, after=8, line=22, first_line=first_line)
    run = p.add_run(text)
    set_run_font(run, size=Pt(BODY_SIZE), color=INK)
    return p


def add_heading_cn(doc, text: str, level: int):
    p = doc.add_paragraph()
    if level == 1:
        set_paragraph_spacing(p, before=16, after=10, line=24)
        run = p.add_run(text)
        set_run_font(run, east=EAST_HEAD, size=Pt(16), bold=True, color=NAVY)
        add_bottom_border(p, sz="8")
    else:
        set_paragraph_spacing(p, before=12, after=6, line=22)
        run = p.add_run(text)
        set_run_font(run, east=EAST_HEAD, size=Pt(13), bold=True, color=NAVY)
    return p


def add_caption(doc, text: str):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_paragraph_spacing(p, before=4, after=12, line=18)
    run = p.add_run(text)
    set_run_font(run, size=Pt(10.5), color=MUTED)
    return p


def add_table(doc, headers: list[str], rows: list[list[str]]):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(h)
        set_run_font(run, east=EAST_HEAD, size=Pt(10.5), bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
        shade_cell(cell, "1F4E79")
        set_cell_border(cell)
    for r_i, row in enumerate(rows):
        fill = "F2F6FB" if r_i % 2 == 0 else "FFFFFF"
        for c_i, val in enumerate(row):
            cell = table.rows[r_i + 1].cells[c_i]
            cell.text = ""
            p = cell.paragraphs[0]
            run = p.add_run(val)
            set_run_font(run, size=Pt(10.5), color=INK)
            shade_cell(cell, fill)
            set_cell_border(cell)
    doc.add_paragraph()
    return table


def add_picture(doc, path: Path, width_cm: float = 15.6):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_paragraph_spacing(p, before=8, after=2, line=18)
    run = p.add_run()
    run.add_picture(str(path), width=Cm(width_cm))


def add_header_footer(section):
    header = section.header
    header.is_linked_to_previous = False
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = hp.add_run("专题研究报告  ·  Tesla Cybercab 机动车身份与保险监管口径")
    set_run_font(run, size=Pt(9), color=MUTED)
    add_bottom_border(hp, color="8FAADC", sz="6")

    footer = section.footer
    footer.is_linked_to_previous = False
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = fp.add_run("仅供研究参阅，不构成法律、投保或投资建议    第 ")
    set_run_font(run, size=Pt(9), color=MUTED)

    def add_field(paragraph, instr: str):
        r1 = paragraph.add_run()
        fld1 = OxmlElement("w:fldChar")
        fld1.set(qn("w:fldCharType"), "begin")
        r1._r.append(fld1)
        r2 = paragraph.add_run()
        t = OxmlElement("w:instrText")
        t.set(qn("xml:space"), "preserve")
        t.text = instr
        r2._r.append(t)
        r3 = paragraph.add_run()
        fld3 = OxmlElement("w:fldChar")
        fld3.set(qn("w:fldCharType"), "end")
        r3._r.append(fld3)

    add_field(fp, " PAGE ")
    run = fp.add_run(" 页")
    set_run_font(run, size=Pt(9), color=MUTED)


def build_document(path: Path) -> Path:
    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(2.6)
    section.right_margin = Cm(2.6)
    section.top_margin = Cm(2.4)
    section.bottom_margin = Cm(2.4)
    section.header_distance = Cm(1.2)
    section.footer_distance = Cm(1.2)
    add_header_footer(section)

    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(BODY_SIZE)
    normal.font.color.rgb = INK
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), EAST)

    # ----- cover -----
    for _ in range(3):
        doc.add_paragraph()
    k = doc.add_paragraph()
    k.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = k.add_run("专题研究报告")
    set_run_font(run, east=EAST_HEAD, size=Pt(14), bold=True, color=NAVY)

    line = doc.add_paragraph()
    line.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_bottom_border(line, sz="18")

    t1 = doc.add_paragraph()
    t1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_paragraph_spacing(t1, before=18, after=6, line=32)
    run = t1.add_run("Tesla Cybercab 在美国的机动车法律身份")
    set_run_font(run, east=EAST_HEAD, size=Pt(22), bold=True, color=INK)

    t2 = doc.add_paragraph()
    t2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_paragraph_spacing(t2, before=0, after=12, line=32)
    run = t2.add_run("与相关监管要求的保险类型")
    set_run_font(run, east=EAST_HEAD, size=Pt(22), bold=True, color=INK)

    en = doc.add_paragraph()
    en.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_paragraph_spacing(en, before=4, after=18, line=20)
    run = en.add_run("Vehicle Classification and Statutory Insurance Requirements\nfor Tesla Cybercab in the United States")
    set_run_font(run, size=Pt(11), color=MUTED)

    meta_rows = [
        ("报告类型", "海外车险监管专题研究"),
        ("研究问题", "Cybercab 是否属于美国联邦法上的机动车；相关监管要求哪一类保险"),
        ("资料范围", "美国联邦与州监管原文、公开英文报道；未使用中文媒体作为事实来源"),
        ("截稿日期", "2026年9月4日"),
        ("版本", "研究报告稿，非网站文章排版"),
    ]
    table = doc.add_table(rows=len(meta_rows), cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (k_txt, v_txt) in enumerate(meta_rows):
        c0, c1 = table.rows[i].cells
        c0.text = ""
        p0 = c0.paragraphs[0]
        r0 = p0.add_run(k_txt)
        set_run_font(r0, east=EAST_HEAD, size=Pt(11), bold=True, color=NAVY)
        shade_cell(c0, "E7EEF7")
        set_cell_border(c0)
        c1.text = ""
        p1 = c1.paragraphs[0]
        r1 = p1.add_run(v_txt)
        set_run_font(r1, size=Pt(11), color=INK)
        set_cell_border(c1)
        c0.width = Cm(3.4)
        c1.width = Cm(12.2)

    note = doc.add_paragraph()
    note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_paragraph_spacing(note, before=28, after=0, line=18)
    run = note.add_run("本文不构成法律意见、投保建议、承保决策或投资建议。\n判断部分为作者基于公开材料的研究整理，不代表任何机构观点。")
    set_run_font(run, size=Pt(10), color=MUTED)

    doc.add_page_break()

    # ----- abstract -----
    add_heading_cn(doc, "摘要", 1)
    add_body(
        doc,
        "Tesla Cybercab 为两座、无方向盘与踏板的 Robotaxi 车型。2026 年第一季度在得克萨斯超级工厂启动生产；"
        "2026年9月3日奥斯汀发布会前后，Tesla Robotaxi, LLC 已将 VIN 前缀 5YJA 的车辆写入德州机动车承运人资质系统。"
        "公开查询一度显示 45 台 Cybercab，与 Model Y 合计授权约 420 台。",
    )
    add_body(
        doc,
        "研究结论分三层。第一，按 49 U.S.C. §30102，Cybercab 属于联邦法上的机动车；方向盘、踏板与人类驾驶人并非构成要件。"
        "NHTSA 2016 年解释函与 2022 年乘员保护终规（87 FR 18560）把无传统操控件的自动驾驶车辆继续放在机动车安全标准之内。"
        "Tesla 主张按联邦机动车安全标准自我认证，因此不进入 49 CFR Part 555 每 12 个月 2,500 辆的临时豁免上限。",
    )
    add_body(
        doc,
        "第二，联邦《机动车安全法》不规定自动驾驶保险险种或限额。保险义务来自州财务责任法，并随测试、部署、网约载客叠加。"
        "德州当前部署要求机动车责任险或自保；保险法把自动化机动车视同运输网络公司司机，预约定程综合限额 100 万美元。"
        "加州若以无人驾驶载客进入自动驾驶项目，制造商测试与公用事业委员会客运许可各要求 500 万美元财务责任。",
    )
    add_body(
        doc,
        "第三，核保变量是行程状态与许可层级。待单、预约定程、测试许可与客运许可对应不同下限；"
        "分项限额、综合限额与制造商财务责任不可直接横比。Tesla 尚未公布 Cybercab 保单样本；私人乘用车保单不能覆盖车队网约运营。",
    )
    kw = doc.add_paragraph()
    set_paragraph_spacing(kw, before=6, after=10, line=20, first_line=0)
    run = kw.add_run("关键词：")
    set_run_font(run, east=EAST_HEAD, size=Pt(12), bold=True, color=NAVY)
    run = kw.add_run("Tesla Cybercab；机动车；FMVSS 自我认证；运输网络公司责任险；SB 2807；加州车辆法典第 38750 条")
    set_run_font(run, size=Pt(12), color=INK)

    add_heading_cn(doc, "目录", 1)
    toc_items = [
        "一、研究背景与问题界定",
        "二、联邦层面的机动车认定",
        "三、自我认证路径与豁免上限",
        "四、保险义务的分层结构",
        "五、德克萨斯州：当前部署地的保险口径",
        "六、加利福尼亚州对照",
        "七、产品责任与尚未公开的保单",
        "八、对国内财产险承保的启示",
        "九、后续跟踪事项",
        "附录一  主要英文来源",
        "附录二  局限与口径说明",
    ]
    for item in toc_items:
        p = doc.add_paragraph()
        set_paragraph_spacing(p, before=2, after=2, line=22, first_line=0)
        run = p.add_run(item)
        set_run_font(run, size=Pt(12), color=INK)

    # ----- 1 -----
    add_heading_cn(doc, "一、研究背景与问题界定", 1)
    add_body(
        doc,
        "Cybercab 的产品形态与传统乘用车不同：两座、无方向盘与踏板，面向 Robotaxi 载客。"
        "分类问题决定强制责任险是否适用；用途问题决定限额落在哪一档。二者必须分开处理。"
        "本报告只回答两个问题：该车在美国联邦法上是否属于机动车；相关监管要求的保险属于哪一类、限额如何确定。",
    )
    add_body(
        doc,
        "事实材料取自美国联邦与州监管原文，以及英文公开报道。生产与自我认证主张转述 Electrek 对 Tesla 2026 年第一季度财报电话会的报道；"
        "德州名册数字转述 TeslaNorth、Teslarati 对 TxMCCS 公开查询的报道。未获得保单样本或出险率，也不使用中文媒体作为事实来源。",
    )

    # ----- 2 -----
    add_heading_cn(doc, "二、联邦层面的机动车认定", 1)
    add_body(
        doc,
        "机动车定义写在 49 U.S.C. §30102(a)(7)：由机械动力驱动或牵引、主要为公共街道、道路与公路制造的车辆；仅在轨道上运行的车辆除外。"
        "Cybercab 以公共道路载客为设计用途，满足该定义。条文未将方向盘、踏板或人类驾驶人列为构成要件。",
    )
    add_body(
        doc,
        "国家公路交通安全管理局 2016 年 2 月 4 日致 Google 自动驾驶项目负责人的解释函，针对去掉方向盘与踏板之后联邦机动车安全标准如何适用。"
        "该函把自动驾驶系统视为机动车设备；在 Google 所述设计下，把「驾驶人」解释为该系统，并写明车辆仍须按当时有效的联邦机动车安全标准自我认证。"
        "解释不能改写须经规则制定或豁免才能调整的条文。2016 年仍有若干标准以脚控制动、转向管柱为前提，影响的是认证路径，不改变车辆的机动车身份。",
    )
    add_body(
        doc,
        "2022 年 3 月 30 日，《联邦公报》87 FR 18560 发布《配备自动驾驶系统车辆的乘员保护》终规，2022 年 9 月 26 日生效。"
        "终规修改 200 系列碰撞防护标准的用语，使「驾驶人座位」「方向盘」等表述能够适用于没有传统操控件的自动驾驶车辆，"
        "并写明此类车辆仍须提供与现行乘用车相当的乘员保护。终规适用于机动车中的乘用车。",
    )
    fig1 = IMG / "classification-path.png"
    if fig1.exists():
        add_picture(doc, fig1)
        add_caption(doc, "图1  Cybercab 联邦机动车认定路径（作者根据公开法条绘制，非官方流程图）")
    add_caption(doc, "表1  联邦认定依据与对 Cybercab 的含义")
    add_table(
        doc,
        ["规范", "对 Cybercab 的含义"],
        [
            ["49 U.S.C. §30102(a)(7)", "公路用机械动力车辆即机动车，条文未要求方向盘或踏板"],
            ["NHTSA 2016-02-04 解释函", "自动驾驶系统属机动车设备；无人类驾驶人时车辆仍须认证"],
            ["87 FR 18560，2022-03-30", "无传统操控件的自动驾驶车辆仍须提供等同碰撞保护"],
            ["49 CFR Part 555", "仅在申请临时豁免时，才受每 12 个月 2,500 辆上限约束"],
        ],
    )
    add_body(
        doc,
        "图1按认定顺序排列：先确认机动车身份，再证明符合安全标准。保险义务以分类为前提，限额不反向改写车辆法律身份。",
        first_line=0.74,
    )

    # ----- 3 -----
    add_heading_cn(doc, "三、自我认证路径与豁免上限", 1)
    add_body(
        doc,
        "美国对新车不设事前型式批准。制造商须自我认证：在制造日符合全部适用的联邦机动车安全标准，并承担缺陷召回。"
        "无法符合个别标准时，可依 49 U.S.C. §30113 与 49 CFR Part 555 申请临时豁免。"
        "除经济困难等少数情形外，申请材料须声明：获豁免车辆在任一 12 个月期内在美国销售不超过 2,500 辆。"
        "该上限约束豁免车辆，不约束已自我认证、宣称符合全部适用标准的车辆。",
    )
    add_body(
        doc,
        "Electrek 对 Tesla 2026 年第一季度财报电话会的报道写明：马斯克确认 Cybercab 已开始生产；"
        "车辆工程副总裁 Lars Moravy 在社交网络上以 “No” 回答 2,500 辆上限是否适用于 Cybercab。"
        "报道同时指出，工厂画面中的车辆已贴联邦合规标签。这是制造商主张。"
        "美国安全法不就单车型发放符合性批准；国家公路交通安全管理局亦未发布 Cybercab 专属批准函。"
        "若后续检测或缺陷调查认定不符合标准，执法与召回仍然适用。",
    )
    add_body(
        doc,
        "德州把同一分类写进州法。参议院 SB 2807 在运输法典增设自动化机动车专章，2026 年 5 月 28 日起对商业无人驾驶载客与载货强制执行："
        "车辆须具备符合联邦法律、包括联邦机动车安全标准的自动驾驶系统，并持有德州机动车管理局授权。"
        "TeslaNorth 与 Teslarati 根据 TxMCCS 公开查询报道：Tesla Robotaxi, LLC 于 2026 年 8 月 31 日起列入 2026 款 Cybercab，"
        "VIN 前缀 5YJA，与 Model Y 的 7SAYG 相区别；同日由 7 台增至 45 台，至发布会当日授权合计约 420 台。"
        "列入名册确认商业运营授权；Robotaxi 应用是否已向普通乘客开放该车型，须另行核对。",
    )

    # ----- 4 -----
    add_heading_cn(doc, "四、保险义务的分层结构", 1)
    add_body(
        doc,
        "联邦《机动车安全法》规范新车性能与缺陷，不规定保单名称或责任限额。美国没有全国统一的 Cybercab 自动驾驶险。"
        "实际义务分三层：上路财务责任、自动驾驶测试或部署许可、网约或包车客运许可。",
    )
    fig2 = IMG / "insurance-stack.png"
    if fig2.exists():
        add_picture(doc, fig2)
        add_caption(doc, "图2  德州与加州法定保险下限分层（作者根据公开法条绘制；金额为法定下限，口径不完全等同）")
    add_caption(doc, "表2  按场景划分的法定保险口径与下限")
    add_table(
        doc,
        ["场景", "法定口径", "下限"],
        [
            ["德州普通上路", "运输法典第 601.072 条", "人身伤害每人 3 万美元、每事故 6 万美元，财产损失 2.5 万美元"],
            ["德州网约待单", "保险法第 1954.052 条", "人身伤害每人 5 万美元、每事故 10 万美元，财产损失 2.5 万美元"],
            ["德州预约定程", "保险法第 1954.053 条", "死亡、人身伤害与财产损失综合限额 100 万美元"],
            ["加州车主财务责任", "车辆法典第 16056 条（2025-01-01 起保单）", "人身伤害每人 3 万美元、每事故 6 万美元，财产损失 1.5 万美元"],
            ["加州制造商测试或部署", "车辆法典第 38750 条及 13 CCR §227.04", "500 万美元保险、保证或自保"],
            ["加州自动驾驶客运项目", "公用事业委员会 D.18-05-043、D.20-11-046", "公共责任与财产损失 500 万美元；有雇员另须工伤补偿"],
        ],
    )
    add_body(
        doc,
        "表2比较的是法定下限，口径并不相同。德州前两档为人身伤害与财产损失分项限额，预约定程为综合限额；"
        "加州 500 万美元是制造商或客运许可的财务责任证明，可用保险、保证或自保满足。产品责任不在这些底线之内。",
    )
    add_body(
        doc,
        "市场保单形态与法定名称需要分开。车队运营方实际购买的多为商用车险责任保障，再按网约或客运许可提高限额；"
        "私人乘用车保单对网约、出租与车队商业使用设有除外。"
        "Tesla Insurance 在华盛顿等地备案的是私人乘用车实时定价产品，不能当作 Cybercab 车队的法定责任险。",
    )

    # ----- 5 -----
    add_heading_cn(doc, "五、德克萨斯州：当前部署地的保险口径", 1)
    add_body(
        doc,
        "SB 2807 把「自动化机动车」定义为安装自动驾驶系统的机动车。运输法典第 545.455 条规定："
        "自动驾驶系统激活时，车辆须由机动车责任保险或自保覆盖，额度等于或高于本州或联邦法律对该车类型与用途所要求的金额。"
        "商业无人驾驶载客另须取得德州机动车管理局授权，并提交应急互动方案。授权申请须书面确认上述保险已经落实。"
        "法律没有另写固定的 500 万美元自动驾驶险；下限按车辆类型与用途确定。部分英文二手报道把加州 500 万美元套到德州条文上，与法案文本不符。",
    )
    add_body(
        doc,
        "同一法案在保险法典增设第 1954.003 条：运输法典定义的自动化机动车，就第 1954 章 B 分章而言视为运输网络公司司机，该分章的承保要求对其适用。"
        "第 1954.052 条：已登录数字网络、可接单但尚未进入预约定程时，责任险至少为人身伤害每人 5 万美元、每事故 10 万美元，财产损失 2.5 万美元。"
        "第 1954.053 条：处于预约定程时，死亡、人身伤害与财产损失综合限额至少 100 万美元，并在本州要求的范围内提供未投保驾驶人与人身伤害保护。"
        "职业法典第 2402 章同步把通过数字网络安排的自动化机动车行程纳入运输网络公司规则。",
    )
    add_body(
        doc,
        "自动驾驶系统激活时，该系统为交通与机动车法律意义上的操作者；违法通知可向车辆所有人或授权持有人送达。"
        "公开名册上的持有人是 Tesla Robotaxi, LLC。对保险人而言，被保险人应为运营实体与登记所有人；驾驶人座位是否有人，不构成承保前提。"
        "私人乘用车保单的合同载客除外，会把赔付指向车队商用车险与运输网络公司责任保障。",
    )
    add_body(
        doc,
        "列入名册须维持保险。应用是否已向普通乘客派发 Cybercab，须另行核对。"
        "TeslaNorth 写明：授权清单是监管上限，实时派单数需另行核对。"
        "核保应核对授权持有人、VIN 清单、数字网络是否已将该车型纳入预约定程，以及出险时车辆处于待单还是载客。",
    )

    # ----- 6 -----
    add_heading_cn(doc, "六、加利福尼亚州对照", 1)
    add_body(
        doc,
        "加州把自动驾驶汽车测试与部署写进车辆法典第 16.6 编。第 38750 条要求：制造商在本州公共道路开始测试前，"
        "须取得 500 万美元的保险、保证或自保证明，并按机动车管理局规定提交。部署许可同样要求维持该金额。"
        "加州法规汇编第 13 编第 227.04 条把证明形式限定为：加州持牌保险人出具的保险、持牌或合格溢额保证、或自保证书；"
        "自保须提交近三年经审计净资产不低于 500 万美元的报表。该 500 万美元针对制造商对人身伤害、死亡与财产损失判决的偿付能力，"
        "与车主依第 16056 条承担的普通财务责任并行。",
    )
    add_body(
        doc,
        "载客收费另受加州公用事业委员会管辖。委员会自动驾驶客运试点与一期部署项目要求公共责任与财产损失保险 500 万美元，"
        "高于包车承运人通则第 115 号系列的普通限额；有雇员时另须工伤补偿。保险人须向委员会电子备案，证明保单持续有效。",
    )
    add_body(
        doc,
        "2026 年 3 月，委员会消费者政策、交通与执法副执行主任 Pat Tsen 在访谈中说明："
        "Tesla 在加州的约车服务按有人驾驶的包车客运管理，未进入自动驾驶客运项目。"
        "加州把自动驾驶定义为驾驶自动化 3 级及以上，Tesla 系统按 2 级管理。"
        "Tesla 持有的是包车承运许可，与礼宾车公司同类；坐在驾驶人座位上的人被认定为驾驶人。"
        "Electrek 于 2026 年 3 月 25 日报道该谈话。TechCrunch 在 2025 年许可获批时已写明："
        "该包车许可不覆盖自动驾驶测试或部署，Tesla 当时未申请委员会自动驾驶客运项目，也未持有加州机动车管理局的无人驾驶载客许可。",
    )
    add_body(
        doc,
        "无方向盘的 Cybercab 若在加州向公众提供无人驾驶行程，将同时需要机动车管理局自动驾驶许可与委员会自动驾驶客运许可，"
        "保险口径从包车通则升至制造商 500 万美元加客运 500 万美元。"
        "在该许可完成前，加州现行 Tesla 约车仍按有人驾驶的包车责任险管理。",
    )

    # ----- 7 -----
    add_heading_cn(doc, "七、产品责任与尚未公开的保单", 1)
    add_body(
        doc,
        "上述条文要求的都是机动车第三者责任及其在测试、网约、客运许可中的加高限额，可以用保险、保证或自保满足。"
        "软件缺陷、错误的最小风险策略、远程坐席失误，仍可能进入产品责任或专业责任索赔。"
        "联邦与德州、加州的财务责任法都没有把产品责任险规定为上路前提。"
        "出险后，索赔先指向机动车责任险限额；限额不足或争议集中于设计缺陷时，再进入产品责任。",
    )
    add_body(
        doc,
        "Tesla 没有公布 Cybercab 的保单名称、承保人、是否自保、限额是否高于法定下限。"
        "马斯克多次把 Robotaxi 运营成本目标说成约每英里 0.20 美元，其中含保险成本假设。这是企业内部定价口径，不能替代法定保单。"
        "核保应核对：Tesla Robotaxi, LLC 的商用车险责任限额、是否批注运输网络公司分阶段保障、超额责任是否存在、"
        "远程协助人员是否纳入工伤补偿，以及产品责任是否由制造商保单承接。",
    )

    # ----- 8 -----
    add_heading_cn(doc, "八、对国内财产险承保的启示", 1)
    add_body(
        doc,
        "可迁移的观察有三条。第一，先完成机动车分类，再谈保险；无方向盘不能单独改写强制责任险的适用。"
        "第二，同一辆车在待单、载客、测试、跨州时限额不同，保单必须按行程状态切换，一张「智驾险」无法覆盖全部状态。"
        "第三，制造商 500 万美元财务责任与客运 500 万美元公共责任是许可门槛；定价仍须回到车队里程、运营设计域与软件版本。",
    )

    # ----- 9 -----
    add_heading_cn(doc, "九、后续跟踪事项", 1)
    items = [
        "自我认证能否在检测与缺陷调查中成立。国家公路交通安全管理局若认定碰撞防护、灯光或制动标准未满足，执法路径是缺陷调查与召回。每 12 个月 2,500 辆的豁免上限不会自动适用于已自我认证车辆，但认证主张可被推翻。",
        "德州名册何时形成可派单运力。跟踪 Tesla Robotaxi 应用是否派发 5YJA 前缀车辆，以及出险记录是否按第 1954 章分阶段限额赔付。",
        "加州许可是否升级。无方向盘载客需要机动车管理局自动驾驶许可与委员会自动驾驶项目；一旦申请，500 万美元财务责任将成为可核对的备案材料。",
        "实际保单是否高于法定下限。100 万美元与 500 万美元都是许可门槛。严重伤亡事故的判决可能高于门槛，超额责任与再保安排目前未见披露。",
        "产品责任与机动车责任如何分单。感知误判、远程坐席指令与车辆机械故障若由不同保单承接，追偿顺序将决定案均赔付落在哪一份合同上。",
    ]
    for i, text in enumerate(items, 1):
        p = doc.add_paragraph()
        set_paragraph_spacing(p, after=6, line=22, first_line=0)
        run = p.add_run(f"{i}. {text}")
        set_run_font(run, size=Pt(BODY_SIZE), color=INK)

    # ----- appendix 1 -----
    add_heading_cn(doc, "附录一  主要英文来源", 1)
    add_body(
        doc,
        "下列来源均为英文监管原文或英文公开报道。中文为作者转写。站内其他中文稿件仅作延伸阅读，不作为本报告事实依据。",
        first_line=0,
    )
    refs = [
        "49 U.S.C. §30102. Definitions. https://uscode.house.gov/",
        "NHTSA, Interpretation letter to Google, Inc., Feb. 4, 2016. https://www.nhtsa.gov/interpretations/google-compiled-response-12-nov-15-interp-request-4-feb-16-final",
        "Occupant Protection for Vehicles With Automated Driving Systems, 87 Fed. Reg. 18560 (Mar. 30, 2022). https://www.govinfo.gov/content/pkg/FR-2022-03-30/html/2022-05426.htm",
        "49 CFR Part 555, Temporary Exemption from Motor Vehicle Safety and Bumper Standards. https://www.ecfr.gov/current/title-49/part-555",
        "NHTSA interpretation GF005146 (Part 555 2,500-vehicle cap; no carry-forward).",
        "Texas S.B. 2807, 89th Leg., R.S. (enrolled). https://capitol.texas.gov/tlodocs/89R/billtext/html/SB02807F.HTM",
        "Tex. Transp. Code §545.455, §601.072.",
        "Tex. Ins. Code §§1954.003, 1954.052, 1954.053.",
        "Cal. Veh. Code §§16056, 38750; Cal. Code Regs. tit. 13, §227.04.",
        "CPUC, Autonomous Vehicle Program Applications—General Guidance (Aug. 2024); Decision 18-05-043; Decision 20-11-046.",
        "Electrek, “Tesla confirms Cybercab production has started despite delays in unsupervised driving,” Apr. 23, 2026.",
        "Electrek, “California regulator confirms Tesla is not operating an autonomous vehicle service,” Mar. 25, 2026.",
        "TechCrunch, “What Tesla can and can’t do in California with its new passenger transportation permit,” Mar. 18, 2025.",
        "TeslaNorth, “Tesla Cybercab Just Made Texas’s Official Robotaxi Roster,” Sept. 1, 2026; “Tesla Robotaxi Roster Hits 420 Vehicles,” Sept. 2, 2026.",
        "Teslarati, “Tesla Cybercab fleet grows in Austin ahead of launch event.”",
    ]
    for i, ref in enumerate(refs, 1):
        p = doc.add_paragraph()
        set_paragraph_spacing(p, after=4, line=18, first_line=0)
        run = p.add_run(f"[{i}]  {ref}")
        set_run_font(run, size=Pt(10.5), color=INK)

    # ----- appendix 2 -----
    add_heading_cn(doc, "附录二  局限与口径说明", 1)
    limits = [
        "联邦定义与安全标准以 49 U.S.C. 第 301 章、NHTSA 2016-02-04 解释函、87 FR 18560 及 49 CFR Part 555 为准；Tesla 自我认证为制造商主张，监管机构未发布 Cybercab 专属批准。",
        "德州保险与授权条文以 SB 2807 入法文本、运输法典第 545.455 条、保险法第 1954 章为准。TxMCCS 台数转述 TeslaNorth 与 Teslarati 对公开查询的报道，名册实时变动，截稿日为 2026-09-04。",
        "加州 500 万美元要求引自车辆法典第 38750 条、13 CCR §227.04 及公用事业委员会自动驾驶项目指引；Tsen 谈话转述 Electrek 2026-03-25。Tesla 现行加州约车许可可能在截稿后变更。",
        "图1、图2 由作者根据公开法条绘制，非官方流程图、非现场图。表2金额为法定下限，分项限额与综合限额口径并不等同。",
        "关于保单形态、产品责任分单与国内迁移的表述为作者判断，非企业披露。",
    ]
    for text in limits:
        p = doc.add_paragraph()
        set_paragraph_spacing(p, after=6, line=20, first_line=0)
        run = p.add_run("·  " + text)
        set_run_font(run, size=Pt(10.5), color=INK)

    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    return path


def send_docx(to: str, path: Path, subject: str, body: str) -> None:
    msg = MIMEMultipart()
    msg["From"] = FROM_ADDR
    msg["To"] = to
    msg["Subject"] = Header(subject, "utf-8")
    msg.attach(MIMEText(body, "plain", "utf-8"))
    part = MIMEBase("application", "vnd.openxmlformats-officedocument.wordprocessingml.document")
    part.set_payload(path.read_bytes())
    encoders.encode_base64(part)
    ascii_name = "2026-09-04-Tesla-Cybercab-US-MV-Insurance-Research-Note.docx"
    part.add_header("Content-Disposition", "attachment", filename=ascii_name)
    msg.attach(part)
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx) as s:
        s.login(USERNAME, PASSWORD)
        refused = s.sendmail(FROM_ADDR, [to], msg.as_bytes())
        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--to", default="yanghailin508@pingan.com.cn")
    parser.add_argument("--send", action="store_true")
    args = parser.parse_args()
    out = OUT_DIR / OUT_NAME
    path = build_document(out)
    print(f"wrote {path} ({path.stat().st_size} bytes)", file=sys.stderr)
    if args.send:
        send_docx(
            args.to,
            path,
            "【研究报告】Tesla Cybercab 在美国的机动车身份与保险监管口径",
            "附件为 Word 研究报告稿，按专题研究报告体例重排，不是网站文章版式。\n\n"
            "结构：封面、摘要、目录、九章正文、英文来源附录。含图1认定路径、图2保险分层、表1–表2。\n"
            "事实材料取自美国联邦与州监管原文及英文公开报道。\n"
            "不构成法律、投保或投资建议。",
        )
        print(f"sent to {args.to}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
