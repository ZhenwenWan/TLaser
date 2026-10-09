from pathlib import Path
import shutil

import docx
from docx.oxml.ns import qn
from docx.shared import Pt


SRC = Path(r"C:\Users\aw4wz\Documents\Codex\TLaser\ModuleNew_0814.docx")
OUT = Path(r"C:\Users\aw4wz\Documents\Codex\TLaser\ModuleNew_0814_LiYingsong_smallteam.docx")


def set_font(run, size=10.5):
    run.font.name = "仿宋"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "仿宋")
    run._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
    run._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    run.font.size = Pt(size)


def replace_para(paragraph, text):
    paragraph.clear()
    run = paragraph.add_run(text)
    set_font(run)


def replace_cell(cell, text):
    for p in cell.paragraphs[1:]:
        p._element.getparent().remove(p._element)
    replace_para(cell.paragraphs[0], text)


def para_starts(doc, prefix):
    for p in doc.paragraphs:
        if p.text.strip().startswith(prefix):
            return p
    raise ValueError(f"paragraph not found: {prefix}")


def replace_all_text(doc, old, new):
    for p in doc.paragraphs:
        if old in p.text:
            replace_para(p, p.text.replace(old, new))
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if old in cell.text:
                    replace_cell(cell, cell.text.replace(old, new))


def set_row_values(row, mapping):
    for idx, value in mapping.items():
        if idx < len(row.cells):
            replace_cell(row.cells[idx], value)


shutil.copyfile(SRC, OUT)
doc = docx.Document(OUT)

li_role = "李迎松教授兼职加盟，任科学顾问，负责电磁/微波与智能信号处理技术路线、L-I-V测试数据建模与验证路线、种子客户和产业资源协同"

team_summary = (
    "核心团队采用“小而精”结构，由计算物理、工业软件、电子信息与智能信号处理专家组成。\n"
    "CEO万振文，中科院博士、美国MBL博士后、厦门大学副教授、丹麦DMI资深研究员、国家级人才“启明计划”入选者，麦慎数字科技创始人。其长期从事多物理场数值模式、CAE算法和工业软件开发，完成EML高频电磁仿真、MySim多物理场仿真等软件原型，并服务清华大学深圳研究生院、天津科技大学、上海市气象局、北京海基、上海应尧、苏州ShonCloud、EastWave、Ansys中国等高校、科研机构和企业客户。已授权发明专利3项，具备将复杂物理模型工程化为软件产品的经验。\n"
    "科学顾问李迎松，安徽大学电子信息工程学院副院长、教授，计算智能与信号处理教育部重点实验室副主任，安徽省特聘教授人才计划入选者，美国应用计算电磁学学会（ACES）会士，中国通信学会微波技术专委会副主任委员，中国电子学会青年科学家俱乐部理事；公开资料显示，其担任IEEE OJSP领域编辑、IEEE SPL和ACES Journal副主编，入选爱思唯尔中国高被引学者。\n"
    "团队分工与TLaser产品定位一致：万振文全职负责经营、算法、产品和交付；李迎松教授兼职加盟，负责科学顾问、电磁/微波与智能信号处理技术路线、L-I-V测试数据建模与验证路线、种子客户和产业资源协同。苏州麦慎数字科技侧重光通讯激光器7D即时预测、L-I-V数据标定和SaaS工程化。"
)

replace_cell(doc.tables[3].rows[3].cells[0], team_summary)

replace_cell(
    doc.tables[3].rows[14].cells[0],
    (
        "商业模式分三层：1. 联合验证/模型适配服务，按器件型号或项目收费，用于客户L-I-V数据接入、7D参数映射确认、模型标定和验证报告；"
        "2. SaaS订阅，按账号数、器件型号数、数据量和模型库容量收费，适合研发与测试团队持续使用；"
        "3. 私有化部署/API授权，面向头部光模块、激光芯片和测试装备企业，收取部署费、年度授权费和维护费，并接入客户测试台、研发数据库和PLM流程。"
        "市场拓展路径为“真实L-I-V样例-付费试点-年度授权”。先用客户已有测试数据形成校准前后对比报告，再通过模型适配绑定客户器件型号，最后将SaaS模型库、API和私有部署纳入客户研发/测试流程。市场拓展以李迎松教授协调的种子客户及苏州光通信产业链为入口。"
    ),
)

replace_cell(
    doc.tables[3].rows[16].cells[0],
    (
        "第一年：完成苏州公司注册，万振文作为全职核心成员落地，李迎松教授作为兼职科学顾问参与技术路线、测试验证和种子客户协调；完成TLaser V1.0工程版，实现7D设计参数即时性能预测，接入至少1家客户真实L-I-V数据并完成标定验证，主营收入80万元，新增商务/应用工程人员1人。\n"
        "第二年：形成标准SaaS试点版、器件模型库和私有化部署包，完成3家以上付费试点，主营收入350万元，新增光模块测试/应用工程人员1人，核心团队4人。\n"
        "第三年：形成商业版、API接口和标准交付流程，服务不少于6类电信激光器型号，主营收入900万元；团队继续保持小而精结构，采用外部顾问、项目制工程支持和合作伙伴交付补充非核心人力。三年累计受理发明专利5项、PCT 2项、软著6项，完成高企培育/申报和园区/市级科技项目申报。"
    ),
)

replace_para(
    para_starts(doc, "TLaser 面向光通讯半导体激光器研发与测试环节"),
    para_starts(doc, "TLaser 面向光通讯半导体激光器研发与测试环节").text.replace(
        "蒋寻涯教授兼职加盟，任科学顾问，负责光电仿真技术路线、L-I-V测试验证技术路线和种子客户协调对接。",
        li_role + "。"
    ),
)

replace_para(
    para_starts(doc, "本项目以苏州麦慎数字科技有限公司作为园区产业化主体"),
    para_starts(doc, "本项目以苏州麦慎数字科技有限公司作为园区产业化主体").text.replace(
        "蒋寻涯教授以兼职科学顾问方式参与技术路线、L-I-V测试验证和种子客户协调；根据试点进度招聘软件工程、应用工程和销售人员。",
        "李迎松教授以兼职科学顾问方式参与电磁/微波与智能信号处理技术路线、L-I-V测试数据建模和种子客户协调；团队保持小而精，第一年新增商务/应用工程人员1人，第二年新增光模块测试/应用工程人员1人，三年核心团队约4人。"
    ),
)

replace_para(
    para_starts(doc, "项目定位于光电子工业软件"),
    para_starts(doc, "项目定位于光电子工业软件").text.replace(
        "蒋寻涯教授负责协助对接光电仿真、光芯片和测试验证相关种子客户。",
        "李迎松教授负责协助对接电子信息、智能信号处理、微波/电磁仿真和测试验证相关种子客户。"
    ),
)

replace_para(
    para_starts(doc, "商业模式分三步"),
    para_starts(doc, "商业模式分三步").text.replace(
        "第一阶段以万振文直接对接和蒋寻涯协调种子客户为主，第二年建立应用工程和销售团队。",
        "第一阶段以万振文直接对接和李迎松教授协调种子客户为主；第二年补充应用工程能力，核心团队控制在约4人。"
    ),
)

replace_para(
    para_starts(doc, "3-5年阶段目标围绕产品、客户、团队和知识产权展开"),
    (
        "3-5年阶段目标围绕产品、客户、小而精团队和知识产权展开。第一年完成苏州公司注册，形成万振文全职负责、李迎松教授兼职科学顾问支持的小团队结构，完成TLaser V1.0工程版，实现7D设计参数即时性能预测，接入1家以上客户真实L-I-V数据并完成在线标定验证，主营收入约80万元，申请1项发明专利、2项软著，新增商务/应用工程人员1人。第二年完成标准SaaS试点版、器件模型库和私有化部署包，完成3家以上付费试点，主营收入约350万元，申请2项发明专利、1项PCT、2项软著，新增光模块测试/应用工程人员1人，核心团队约4人。第三年完成商业版、API接口和标准交付流程，服务不少于6类电信激光器型号，主营收入约900万元；团队继续保持小而精，通过兼职顾问、项目制工程支持和合作伙伴交付补充非核心能力，累计形成5项发明专利受理、2项PCT、6项软著。\n\n"
        "第四至第五年仍以电信半导体激光器为主线，扩展更多DFB/DBR/FP/泵浦激光器型号、测试温度条件和客户数据接口，形成可复用的激光器模型库和行业案例；在客户需求明确后，再评估VCSEL或其他光电子器件扩展，避免早期产品范围过宽。"
    ),
)

replace_para(
    para_starts(doc, "资金筹措：项目由申报人自筹"),
    para_starts(doc, "资金筹措：项目由申报人自筹").text.replace(
        "主要用于全职核心团队薪酬、软件工程化、测试数据接入、云端算力、知识产权申请和客户联合验证。",
        "主要用于小型全职核心团队薪酬、软件工程化、测试数据接入、云端算力、知识产权申请和客户联合验证。"
    ),
)

replace_para(
    para_starts(doc, "项目以园区科技领军支持"),
    para_starts(doc, "项目以园区科技领军支持").text.replace(
        "资金用于核心研发团队招聘、真实器件测试数据采购、云端平台工程化、客户联合验证、知识产权布局和市场拓展。",
        "资金用于小型核心团队建设、真实器件测试数据采购、云端平台工程化、客户联合验证、知识产权布局和市场拓展。"
    ),
)

replace_para(
    para_starts(doc, "技术风险：真实激光器L-I-V数据可能存在噪声"),
    para_starts(doc, "技术风险：真实激光器L-I-V数据可能存在噪声").text.replace(
        "管理风险：团队跨物理、软件、AI和销售，协同复杂。对策是建立产品负责人、算法负责人、客户交付负责人分工和里程碑管理。",
        "管理风险：小型团队同时覆盖物理、软件、AI和客户交付，资源需要聚焦。对策是保持核心团队约4人，明确产品、算法、客户交付分工，并通过兼职顾问、项目制工程支持和合作伙伴交付补充非核心能力。"
    ),
)

# Align employment indicators with the project-summary staffing plan.
set_row_values(doc.tables[7].rows[4], {1: "4", 2: "2", 3: "4", 4: "4"})
set_row_values(doc.tables[9].rows[1], {2: "2"})
set_row_values(doc.tables[9].rows[4], {2: "4"})
set_row_values(doc.tables[9].rows[7], {2: "4"})
replace_cell(
    doc.tables[9].rows[2].cells[1],
    "完成苏州工业园区公司设立、核心算法代码规范化、TLaser V1.0工程化；实现7D设计参数即时性能预测，接入至少1家试点客户真实L-I-V数据并完成在线标定验证；申请1项发明专利、2项软著，建立云端演示环境；新增商务/应用工程人员1人，形成2人左右全职核心团队。"
)
replace_cell(
    doc.tables[9].rows[5].cells[1],
    "完成标准SaaS试点版、器件模型库、L-I-V数据上传标定流程和客户联合验证；申请2项发明专利、1项PCT、2项软著；形成3个付费试点项目和行业白皮书；新增光模块测试/应用工程人员1人，核心团队约4人。"
)
replace_cell(
    doc.tables[9].rows[8].cells[1],
    "完成商业版平台、API接口、私有化部署能力和标准化交付流程；累计服务不少于6类电信激光器型号，形成8个联合验证/商业项目，主营收入达到900万元；团队继续保持约4人的小而精结构。"
)

# Replace the detailed team member table.
t15 = doc.tables[15]
for cell in t15.rows[0].cells:
    if cell.text.strip() == "蒋寻涯":
        replace_cell(cell, "李迎松")
for cell in t15.rows[2].cells:
    if "中科院百人计划" in cell.text or "复旦大学" in cell.text:
        replace_cell(cell, "安徽大学电子信息工程学院副院长、教授；计算智能与信号处理教育部重点实验室副主任")
for cell in t15.rows[3].cells:
    if "Iowa State University" in cell.text:
        replace_cell(cell, "哈尔滨工程大学")
for cell in t15.rows[4].cells:
    if "物理学/光子学/电磁与光电仿真" in cell.text:
        replace_cell(cell, "信息与通信工程/电磁场与微波技术/智能信号处理")
for cell in t15.rows[6].cells:
    if cell.text.strip() == "上海":
        replace_cell(cell, "安徽合肥")
for cell in t15.rows[9].cells:
    if "复旦大学在职" in cell.text:
        replace_cell(cell, "安徽大学在职，以科学顾问方式兼职加盟，负责电磁/微波与智能信号处理技术路线评审、L-I-V测试数据建模与验证路线设计、种子客户协调对接和产业资源协同。")
for cell in t15.rows[10].cells:
    if "jiangxunya@fudan.edu.cn" in cell.text:
        replace_cell(cell, "提交前补录")

work_rows = {
    13: ("2024.01", "至今", "安徽大学电子信息工程学院", "副院长、教授"),
    14: ("提交前补录", "2024.01", "哈尔滨工程大学信息与通信工程学院", "教授、博士生导师"),
    15: ("2018.12", "至今", "俄罗斯圣彼得堡彼得大帝理工大学", "客座教授"),
    16: ("2018.09", "2018.10", "英国约克大学", "高级访问学者"),
}
for row_idx, vals in work_rows.items():
    row = t15.rows[row_idx]
    set_row_values(row, {
        0: vals[0],
        1: vals[0],
        2: vals[1],
        3: vals[1],
        4: vals[2],
        5: vals[2],
        6: vals[2],
        7: vals[3],
        8: vals[3],
        9: vals[3],
    })

edu_rows = {
    20: ("2011.04", "2014.03", "哈尔滨工程大学", "信息与通信工程", "博士"),
    21: ("2008.09", "2011.03", "哈尔滨工程大学", "信息与通信工程", "硕士"),
    22: ("2004.09", "2006.06", "哈尔滨工程大学", "电子信息相关专业", "本科"),
}
for row_idx, vals in edu_rows.items():
    row = t15.rows[row_idx]
    set_row_values(row, {
        0: vals[0],
        1: vals[0],
        2: vals[1],
        3: vals[1],
        4: vals[2],
        5: vals[2],
        6: vals[2],
        7: vals[3],
        8: vals[3],
        9: vals[4],
        10: vals[4],
    })

replace_cell(
    t15.rows[26].cells[0],
    (
        "就业经历和业绩：李迎松教授为安徽大学电子信息工程学院副院长、教授，计算智能与信号处理教育部重点实验室副主任。公开资料显示，其入选安徽省特聘教授人才计划，担任中国通信学会微波技术专委会副主任委员、中国电子学会青年科学家俱乐部理事，为美国应用计算电磁学学会（ACES）会士，并担任IEEE OJSP领域编辑、IEEE SPL和ACES Journal副主编、Electromagnetic Science和《电子学报》等期刊编委。公开资料显示，李迎松教授入选爱思唯尔中国高被引学者，研究方向涵盖天线、微波、电磁兼容、计算电磁学、智能信号处理及AI应用；其团队已有职务科技成果转化案例。\n\n"
        "与本项目关联：李迎松教授在本项目中兼职加盟，任科学顾问，负责电磁/微波与智能信号处理技术路线评审、激光器L-I-V测试数据建模与验证路线、测试数据与物理模型一致性评审，并协调对接种子客户和产业资源。"
    ),
)
for cell in t15.rows[26].cells[1:]:
    replace_cell(cell, t15.rows[26].cells[0].text)

for old, new in [
    ("蒋寻涯教授", "李迎松教授"),
    ("蒋寻涯", "李迎松"),
    ("复旦大学研究员、博士生导师", "安徽大学电子信息工程学院副院长、教授"),
    ("复旦大学", "安徽大学"),
    ("光电仿真技术路线", "电磁/微波与智能信号处理技术路线"),
    ("光电仿真、光芯片和测试验证", "电子信息、智能信号处理、微波/电磁仿真和测试验证"),
    ("新增就业5人", "新增就业2人"),
    ("新增就业至12人", "核心团队约4人"),
    ("新增就业至25人", "核心团队保持约4人"),
    ("新增就业人数（个） || 25 || 5 || 12 || 25", "新增就业人数（个） || 4 || 2 || 4 || 4"),
]:
    replace_all_text(doc, old, new)

doc.save(OUT)

text = "\n".join(
    [p.text for p in doc.paragraphs]
    + [cell.text for table in doc.tables for row in table.rows for cell in row.cells]
)
print(OUT)
print({k: text.count(k) for k in ["蒋寻涯", "李迎松", "复旦大学", "中科院百人计划", "顾俊", "马戎", "秦三团", "10人", "12人", "25人", "新增就业"]})
