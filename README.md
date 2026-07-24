# AI News Automation & Content Curator

ระบบดึงข้อมูลข่าวสาร AI อัตโนมัติ แปล สรุป และจัดส่งข่าวทางอีเมลประจำวัน พร้อมหน้าเว็บอินเตอร์เฟสสำหรับจัดการไอเดียเนื้อหา (Content Curation) และเขียนโพสต์โซเชียลมีเดียด้วยพลังของ Gemini API

## คุณสมบัติเด่น (Features)
- 🤖 **Daily Automated News Fetcher**: ดึงข่าวสาร AI จาก RSS feed ทั้งภาษาไทยและต่างประเทศ สรุปและแปลเป็นไทยโดยอัตโนมัติ
- 📧 **Outlook & SMTP Email Dispatcher**: จัดส่งอีเมลสรุปข่าวสารจัดแต่งสวยงามด้วยฟอนต์ TH Sarabun New และดีไซน์ที่อ่านง่าย
- 🌐 **Web Content Dashboard**: ระบบหลังบ้านสำหรับเปิดดูข่าวที่บันทึกไว้ เลือกข่าวที่น่าสนใจ และพัฒนาเป็นไอเดียโพสต์ลง Facebook/Social Media
- ✨ **Gemini API Integration**: ช่วยสร้างโพสต์ด้วยโทนเสียงผู้หญิงเล่าเรื่อง (เพื่อนบอกข่าว) ที่เป็นมิตร ดึงดูดสายตา พร้อมหัวข้อที่โดนใจ และสร้าง Image Prompt ภาษาอังกฤษสำหรับนำไปเจนภาพต่อ
- 📅 **Task Scheduler Automation**: มีสคริปต์สําหรับการตั้งค่า Task Scheduler บน Windows ให้รันดึงข่าวและส่งอีเมลตามเวลาที่ต้องการแบบอัตโนมัติทุกวัน

---

## ส่วนประกอบของระบบ (System Components)
1. **`ai_news_fetcher.py`**: สคริปต์ Python หลักสำหรับดึงข่าวจาก RSS, เรียกใช้ Gemini API เพื่อแปล/สรุป, เขียนไฟล์ HTML ล่าสุด และส่งอีเมล
2. **`app.py`**: เว็บเซิร์ฟเวอร์แบบพึ่งพาตัวเอง (Self-contained) พัฒนาด้วย Standard Library ของ Python (ไม่ต้องใช้ `pip install`) สำหรับรัน API และให้บริการหน้าเว็บ
3. **`web/index.html`**: หน้าเว็บ Single Page Application (SPA) คูเรตคอนเทนต์และจัดการโพสต์
4. **`run_web_app.bat`**: ไฟล์ Batch สำหรับรันเว็บเซิร์ฟเวอร์ทันที
5. **`setup_task_scheduler.bat` & `setup_task.ps1`**: สคริปต์สำหรับตั้งรันระบบส่งข่าวอัตโนมัติบน Windows Task Scheduler

---

## ขั้นตอนการติดตั้งและใช้งาน (Setup & Usage)

### 1. การเตรียมไฟล์ตั้งค่าระบบ
1. คัดลอกไฟล์ `config.env.example` แล้วเปลี่ยนชื่อเป็น `config.env`
2. เปิดไฟล์ `config.env` และกรอกข้อมูลที่จำเป็น:
   - ข้อมูลการส่งอีเมล (`SMTP_SERVER`, `SMTP_PORT`, `SENDER_EMAIL`, `SENDER_PASSWORD`, `RECIPIENT_EMAIL`)
   - คีย์ API ของ Gemini (`GEMINI_API_KEY`) เพื่อเปิดใช้ระบบสรุปและสร้างคอนเทนต์

> [!WARNING]
> ห้ามแชร์หรืออัปโหลดไฟล์ `config.env` ขึ้นไปบน Git/GitHub เป็นอันขาด เนื่องจากมีรหัสผ่านและ API key ของคุณอยู่

### 2. การรันเว็บเซิร์ฟเวอร์ (Web Interface)
1. ดับเบิ้ลคลิกไฟล์ `run_web_app.bat` หรือเปิด Terminal/Command Prompt แล้วพิมพ์:
   ```bash
   python app.py
   ```
2. เปิดเบราว์เซอร์ไปที่: `http://localhost:5000`

### 3. การดึงข่าวและจัดส่งอีเมลด้วยตนเอง (Manual Fetch & Send)
สามารถสั่งรันดึงข้อมูลข่าวและส่งอีเมลได้ทันทีผ่าน Command Line:
```bash
# ดึงข่าวและส่งอีเมลตามการตั้งค่าใน config.env
python ai_news_fetcher.py

# ดึงข่าวจำลองแบบ Dry Run (เพื่อดู HTML preview ที่ latest_summary.html โดยไม่ส่งอีเมล)
python ai_news_fetcher.py --dry-run
```

### 4. การตั้งค่าระบบทำงานอัตโนมัติประจำวัน (Windows Task Scheduler)
1. คลิกขวาที่ไฟล์ `setup_task_scheduler.bat` เลือก **Run as administrator** (เรียกใช้ในฐานะผู้ดูแลระบบ)
2. สคริปต์จะทำการสร้าง Task ใน Task Scheduler ของ Windows ให้ทำงานอัตโนมัติในเวลาที่กำหนดไว้ (ค่าเริ่มต้นคือทุกวันเวลา 08:30 น.)
