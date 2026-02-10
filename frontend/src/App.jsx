import { useState, useRef, useEffect } from 'react'
import html2canvas from 'html2canvas'
import './App.css'
import logoImg from './logo.png' 

// --- КОНСТАНТЫ ---
const COLOR_PALETTE = [
  ['#e0f2fe', '#0369a1'], ['#dcfce7', '#15803d'], ['#f3e8ff', '#7e22ce'],
  ['#ffedd5', '#c2410c'], ['#fce7f3', '#be185d'], ['#fee2e2', '#b91c1c'],
  ['#fef9c3', '#a16207'], ['#ccfbf1', '#0f766e'], ['#e0e7ff', '#4338ca'],
  ['#fae8ff', '#86198f'], ['#ecfccb', '#3f6212'], ['#ffe4e6', '#e11d48'],
];

const TEACHERS = ["Adina", "Assel", "Bagdan", "Damir", "Diana", "Erkezhan", "Polina", "Raushan", "Shapagat", "Togzhan", "Yernur"];
const STUDENTS = ["Alizhan", "Amina", "Ayazhan", "Batyrali", "Eskendir", "Kaisar", "Karina", "Madina", "Mukhamadi", "Nurlyzhan", "Olzhas", "Sayazhan", "Sultanali", "Timur", "Turan", "Zeine", "Zere", "Zhasmin", "Alua", "Birganym", "Lyazzat", "Amirkhan"];
const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const ROOMS = ["6 передний", "6 у окна", "8 передний", "8 у окна", "19 передний", "19 у окна"];

// Функция генерации цвета по имени
const getColorForName = (name) => {
  if (!name) return { bg: '#ffffff', border: '#e2e8f0' };
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  const index = Math.abs(hash % COLOR_PALETTE.length);
  const [bg, border] = COLOR_PALETTE[index];
  return { bg, border };
};

// ==========================================
// 1. ВИД: НЕДЕЛЯ (Обычный)
// ==========================================
function ScheduleColumn({ title, placeholder, searchTerm, onSearchTermChange, openModal, refreshKey }) {
  const [response, setResponse] = useState(null)
  const [loading, setLoading] = useState(false)
  const printRef = useRef(null)

  useEffect(() => { 
    if (searchTerm) handleSearch(null, searchTerm); 
  }, [searchTerm, refreshKey]); 

  const handleSearch = async (e, textOverride) => {
    if (e) e.preventDefault()
    const text = textOverride || searchTerm;
    if (!text || !text.trim()) return
    setLoading(true)
    try {
      const res = await fetch('https://amt-schedule.onrender.com', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: text }),
      })
      const data = await res.json()
      setResponse(data)
    } catch (error) { setResponse({ status: 'error', message: 'Ошибка соединения' }) } 
    finally { setLoading(false) }
  }

  const handleDeleteLesson = async (lessonId) => {
    if (!confirm('Удалить урок?')) return;
    try {
      await fetch(`http://127.0.0.1:8000/delete-lesson/${lessonId}`, { method: 'DELETE' });
      handleSearch(null, searchTerm);
    } catch (e) { alert('Ошибка соединения'); }
  }

  const handleDownloadImage = async () => {
    if (!printRef.current || !response) return;
    const canvas = await html2canvas(printRef.current, { scale: 2, backgroundColor: '#ffffff' });
    const link = document.createElement("a");
    link.href = canvas.toDataURL("image/png");
    link.download = `Schedule-${response.person}.png`;
    link.click();
  };

  const renderWeeklyTable = (scheduleData, personName) => {
    const timeSlots = []; for(let h=8;h<21;h++){timeSlots.push(`${h<10?'0'+h:h}:00`);timeSlots.push(`${h<10?'0'+h:h}:30`);}
    const getMinutes = (t) => {const[h,m]=t.split(':').map(Number);return h*60+m;}
    const occupiedCells = new Set();
    
    return (
      <div className="table-wrapper">
        <table className="excel-table">
          <thead><tr><th className="corner-cell">Время</th>{DAYS.map((d,i)=><th key={i}>{d}</th>)}</tr></thead>
          <tbody>
            {timeSlots.map((time, rowIdx) => (
              <tr key={rowIdx}>
                <td className="time-col">{time}</td>
                {DAYS.map((d, colIdx) => {
                  const cellKey = `${colIdx}-${time}`;
                  if (occupiedCells.has(cellKey)) return null;
                  const lesson = scheduleData.find(l => l.day_idx === colIdx && l.start === time);
                  if (lesson) {
                    const dur = getMinutes(lesson.end) - getMinutes(lesson.start);
                    const rowSpan = Math.max(1, Math.round(dur/30));
                    for(let i=1; i<rowSpan; i++) occupiedCells.add(`${colIdx}-${timeSlots[rowIdx+i]}`);
                    
                    // Красим по "другому" человеку (если смотрим учителя - красим по студенту, и наоборот)
                    const other = lesson.student === personName ? lesson.teacher : lesson.student;
                    const c = getColorForName(other);
                    
                    return (
                      <td key={colIdx} rowSpan={rowSpan} className="cell-busy" style={{backgroundColor:c.bg, borderLeft:`4px solid ${c.border}`}}>
                        <div className="lesson-info">
                          <button className="delete-btn" onClick={(e)=>{e.stopPropagation();handleDeleteLesson(lesson.id)}}>×</button>
                          <div className="subj" style={{color:c.border}}>{lesson.subject}</div>
                          <div className="partic">{other}</div>
                          <div className="room-badge">{lesson.room || "Cab 1"}</div>
                          <div className="duration-badge">{lesson.start}-{lesson.end}</div>
                        </div>
                      </td>
                    )
                  }
                  return <td key={colIdx} className="cell-free" onClick={() => openModal(colIdx, time)}>
                    <div className="add-hint">+</div>
                  </td>
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  return (
    <div className="schedule-column">
      <div className="column-header">
        <div className="header-top">
          <h3>{title}</h3>
          {response && response.type === 'weekly_table' && (<button className="export-btn" onClick={handleDownloadImage}>Скачать</button>)}
        </div>
        <form onSubmit={(e) => handleSearch(e)} className="mini-search">
          <input type="text" placeholder={placeholder} value={searchTerm} onChange={(e) => onSearchTermChange(e.target.value)} disabled={loading}/>
          <button type="submit" disabled={loading}>🔍</button>
        </form>
      </div>
      <div className="column-content">
        {response && response.type === 'weekly_table' && <div className="schedule-card full-width" ref={printRef}>{renderWeeklyTable(response.data, response.person)}</div>}
        {response?.status === 'conflict' && <div className="message-card conflict"><h3>⛔ {response.message}</h3></div>}
      </div>
    </div>
  )
}

// ==========================================
// 2. ВИД: КАБИНЕТЫ (Daily)
// ==========================================
function DailyView({ openModal, refreshKey }) {
  const [dayIdx, setDayIdx] = useState(0); 
  const [lessons, setLessons] = useState([]);
  const printRef = useRef(null);

  useEffect(() => {
    fetch('http://127.0.0.1:8000/get-daily-schedule', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ day_idx: dayIdx })
    })
    .then(res => res.json())
    .then(data => setLessons(data.data || []))
  }, [dayIdx, refreshKey]);

  const handleDownload = async () => {
    if (!printRef.current) return;
    const canvas = await html2canvas(printRef.current, { scale: 2, backgroundColor: '#ffffff' });
    const link = document.createElement("a");
    link.href = canvas.toDataURL("image/png");
    link.download = `Rooms-${DAYS[dayIdx]}.png`;
    link.click();
  };

  const handleDelete = async (id) => {
    if(!confirm("Удалить урок?")) return;
    await fetch(`http://127.0.0.1:8000/delete-lesson/${id}`, { method: 'DELETE' });
    const res = await fetch('http://127.0.0.1:8000/get-daily-schedule', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ day_idx: dayIdx })
    });
    const data = await res.json();
    setLessons(data.data);
  }

  const renderTable = () => {
    const timeSlots = []; for(let h=9;h<19;h++){timeSlots.push(`${h<10?'0'+h:h}:00`);timeSlots.push(`${h<10?'0'+h:h}:30`);}
    const getMin = (t) => {const[h,m]=t.split(':').map(Number);return h*60+m;}
    const occupied = new Set(); 

    return (
      <div className="schedule-card full-width" ref={printRef} style={{marginTop:0, padding:0, overflow:'hidden'}}>
        
        {/* Шапка для печати */}
        <div className="print-header-brand" style={{
            background:'white', borderBottom:'3px solid #f97316', padding:'15px 20px',
            display:'flex', alignItems:'center', gap:'20px'
        }}>
           <img src={logoImg} alt="AMT" style={{height:'50px', objectFit:'contain'}}/>
           <div>
             <h2 style={{margin:0, color:'#0f172a', fontSize:'1.5rem'}}>{DAYS[dayIdx]}</h2>
             <span style={{color:'#64748b', fontSize:'0.9rem', fontWeight:600}}>Расписание по кабинетам</span>
           </div>
        </div>

        <div className="table-wrapper">
          <table className="excel-table">
            <thead>
              <tr>
                <th className="corner-cell">Время</th>
                {ROOMS.map((r, i) => <th key={i} style={{minWidth:'90px'}}>{r}</th>)}
              </tr>
            </thead>
            <tbody>
              {timeSlots.map((time, rIdx) => (
                <tr key={rIdx}>
                  <td className="time-col">{time}</td>
                  {ROOMS.map((room, cIdx) => {
                    const key = `${cIdx}-${time}`;
                    if (occupied.has(key)) return null;

                    const l = lessons.find(x => x.room === room && x.start === time);
                    if (l) {
                      const dur = getMin(l.end) - getMin(l.start);
                      const span = Math.max(1, Math.round(dur/30));
                      for(let i=1; i<span; i++) occupied.add(`${cIdx}-${timeSlots[rIdx+i]}`);
                      
                      // 👇 ГЛАВНОЕ ИЗМЕНЕНИЕ: КРАСИМ ПО УЧИТЕЛЮ
                      const col = getColorForName(l.teacher);
                      
                      return (
                        <td key={cIdx} rowSpan={span} className="cell-busy" 
                            style={{backgroundColor: col.bg, borderLeft: `4px solid ${col.border}`}}>
                          <div className="lesson-info">
                             <button className="delete-btn" onClick={(e)=>{e.stopPropagation();handleDelete(l.id)}}>×</button>
                             {/* Отображаем: Предмет, Учитель, Студент */}
                             <div className="subj" style={{fontSize:'0.75rem', fontWeight:'900', color:col.border}}>{l.subject}</div>
                             <div className="partic" style={{fontSize:'0.7rem', fontWeight:'600'}}>{l.teacher}</div>
                             <div className="partic" style={{fontSize:'0.7rem', fontStyle:'italic'}}>{l.student}</div>
                             <div className="duration-badge">{l.start}-{l.end}</div>
                          </div>
                        </td>
                      )
                    }
                    return (
                      <td key={cIdx} className="cell-free" onClick={() => openModal(dayIdx, time, room)}>
                        <div className="add-hint">+</div>
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    )
  }

  return (
    <div className="daily-view-container">
      <div className="daily-header-bar" style={{display:'flex', justifyContent:'space-between', alignItems:'center', background:'#f1f5f9', padding:'8px 12px', borderRadius:'8px 8px 0 0'}}>
          <div className="daily-controls" style={{display:'flex', gap:'1px', flex:1}}>
            {DAYS.map((d, i) => (
              <button key={i} className={`day-btn ${dayIdx===i ? 'active' : ''}`} onClick={()=>setDayIdx(i)}>
                {d}
              </button>
            ))}
          </div>
          <button className="export-btn" onClick={handleDownload} style={{marginLeft:'15px', padding:'8px 16px', fontSize:'0.9rem'}}>
            Скачать
          </button>
      </div>
      {renderTable()}
    </div>
  )
}

// ==========================================
// 3. ГЛАВНОЕ ПРИЛОЖЕНИЕ
// ==========================================
function App() {
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef(null)
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [leftSearch, setLeftSearch] = useState("Расписание Adina")
  const [rightSearch, setRightSearch] = useState("")
  const [activeTarget, setActiveTarget] = useState('left'); 
  const [viewMode, setViewMode] = useState('split'); 

  const [showModal, setShowModal] = useState(false);
  const [modalData, setModalData] = useState({ dayIdx: 0, startTime: '', teacher: '', student: '', subject: 'Math', room: ROOMS[0], duration: 60 });
  
  const [refreshTrigger, setRefreshTrigger] = useState(0); 

  const openModal = (dayIdx, startTime, prefilledRoom = null) => {
    setModalData(prev => ({ 
      ...prev, dayIdx, startTime, room: prefilledRoom || ROOMS[0], teacher: '', student: '' 
    }));
    setShowModal(true);
  }

  const handleSaveManual = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('http://127.0.0.1:8000/add-lesson-manual', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          teacher: modalData.teacher, student: modalData.student, subject: modalData.subject,
          room: modalData.room, day_idx: modalData.dayIdx, start_time: modalData.startTime, duration: parseInt(modalData.duration) 
        }),
      });
      const data = await res.json();
      if (data.status === 'success') { 
        setShowModal(false); 
        setRefreshTrigger(prev => prev + 1); 
      } else { alert(data.message); }
    } catch (error) { alert('Ошибка сохранения'); }
  }

  const handleFileChange = async (event) => {
      const files = event.target.files; if (!files.length) return; setUploading(true);
      const formData = new FormData(); for (let i = 0; i < files.length; i++) formData.append('files', files[i]);
      try { await fetch('http://127.0.0.1:8000/upload', { method: 'POST', body: formData }); alert('Загружено!'); } 
      catch { alert('Ошибка'); } finally { setUploading(false); }
  }

  const handleMenuClick = (name) => {
    const text = `Расписание ${name}`;
    if (activeTarget === 'left') setLeftSearch(text); else setRightSearch(text);
  }

  return (
    <div className="app-container">
      <header className="top-bar">
        <div className="left-section">
          <button className="menu-toggle-btn" onClick={() => setIsSidebarOpen(!isSidebarOpen)}>☰</button>
          <img src={logoImg} alt="Logo" className="app-logo" />
        </div>
        
        <div className="view-selector" style={{display:'flex', gap:'5px', background:'#f1f5f9', padding:'4px', borderRadius:'8px'}}>
          <button 
            style={{border:'none', padding:'6px 12px', borderRadius:'6px', background: viewMode==='split'?'white':'transparent', boxShadow: viewMode==='split'?'0 1px 2px rgba(0,0,0,0.1)':'none', cursor:'pointer'}}
            onClick={()=>setViewMode('split')}>
            На неделю
          </button>
          <button 
            style={{border:'none', padding:'6px 12px', borderRadius:'6px', background: viewMode==='rooms'?'white':'transparent', boxShadow: viewMode==='rooms'?'0 1px 2px rgba(0,0,0,0.1)':'none', cursor:'pointer'}}
            onClick={()=>setViewMode('rooms')}>
            По кабинетам
          </button>
        </div>

        {viewMode === 'split' && (
          <div className="target-selector">
            <span>Поиск в: </span>
            <button className={activeTarget==='left'?'active':''} onClick={()=>setActiveTarget('left')}>⬅️ Лево</button>
            <button className={activeTarget==='right'?'active':''} onClick={()=>setActiveTarget('right')}>Право ➡️</button>
          </div>
        )}

        <div className="actions">
          <input type="file" multiple ref={fileInputRef} onChange={handleFileChange} style={{ display: 'none' }} accept=".csv"/>
          <button className="upload-btn" onClick={() => fileInputRef.current.click()} disabled={uploading}>{uploading ? '⏳' : '📂 CSV'}</button>
        </div>
      </header>

      <div className="main-layout">
        <aside className={`sidebar ${isSidebarOpen ? 'open' : 'closed'}`}>
          <div className="sidebar-section"><h4>Учителя</h4><ul>{TEACHERS.map(t => <li key={t} onClick={() => handleMenuClick(t)}>{t}</li>)}</ul></div>
          <div className="sidebar-section"><h4>Студенты</h4><ul>{STUDENTS.map(s => <li key={s} onClick={() => handleMenuClick(s)}>{s}</li>)}</ul></div>
        </aside>

        <div className="content-area" style={{flex:1, display:'flex', overflow:'hidden'}}>
          {viewMode === 'split' ? (
            <div className="split-view">
              <ScheduleColumn title="Левая панель" placeholder="Поиск..." searchTerm={leftSearch} onSearchTermChange={setLeftSearch} openModal={openModal} refreshKey={refreshTrigger}/>
              <ScheduleColumn title="Правая панель" placeholder="Поиск..." searchTerm={rightSearch} onSearchTermChange={setRightSearch} openModal={openModal} refreshKey={refreshTrigger}/>
            </div>
          ) : (
            <div className="daily-wrapper" style={{flex:1, padding:'20px', display:'flex', flexDirection:'column'}}>
               <DailyView openModal={openModal} refreshKey={refreshTrigger}/>
            </div>
          )}
        </div>
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h3>{DAYS[modalData.dayIdx]} в {modalData.startTime}</h3>
            <form onSubmit={handleSaveManual}>
              <div className="form-row">
                <div style={{flex:1}}>
                  <label>Учитель:</label>
                  <select value={modalData.teacher} onChange={e=>setModalData({...modalData, teacher: e.target.value})} required>
                    <option value="">Выберите...</option>{TEACHERS.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div style={{flex:1}}>
                  <label>Кабинет:</label>
                  <select value={modalData.room} onChange={e=>setModalData({...modalData, room: e.target.value})}>
                    {ROOMS.map(r => <option key={r} value={r}>{r}</option>)}
                  </select>
                </div>
              </div>

              <label>Студент:</label>
              <select value={modalData.student} onChange={e=>setModalData({...modalData, student: e.target.value})} required>
                <option value="">Выберите...</option>{STUDENTS.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <label>Предмет:</label>
              <input type="text" value={modalData.subject} onChange={e=>setModalData({...modalData, subject: e.target.value})} placeholder="Math..." required/>
              <label>Длительность:</label>
              <select value={modalData.duration} onChange={e=>setModalData({...modalData, duration: e.target.value})}>
                <option value="30">30 мин</option><option value="60">60 мин</option><option value="90">90 мин</option><option value="120">120 мин</option>
              </select>
              <div className="modal-actions">
                <button type="button" onClick={() => setShowModal(false)}>Отмена</button>
                <button type="submit" className="save-btn">Сохранить</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default App