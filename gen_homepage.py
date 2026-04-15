import base64
import os

base_dir = r"c:\Users\DIEGO\Documents\PROJETO FLOTADOR"
tmpl_path = r"c:\Users\DIEGO\Documents\PROJETO FLOTADOR\predictive-maintenance-dashboard\homepage.html"
out_path = tmpl_path

# --- DATA ---
fotos = [
    ("Diego Rodrigues", "foto diego_sq.jpeg", "Engenharia de Sistemas", "https://www.linkedin.com/in/diego-rodrigues-7b8330112"),
    ("Guilherme Marcondes", "foto guilherme.png", "Engenharia Mecânica | Integridade & Inspeção Offshore", "https://www.linkedin.com/in/guilherme-marcondes-offshore"),
    ("Mellany Esperidião", "foto mellany.png", "Engenheira de Produção | Gestão de Operações e Manutenção", "https://www.linkedin.com/in/mellany-esperidi%C3%A3o-793846235"),
    ("Allyson Andrew", "foto allyson.png", "Especialista em Ensaios e Monitoramento Ambiental", "https://www.linkedin.com/in/allyson-andrew-silva-oliveira-0b7462187/"),
]

def b64img(fname):
    if not fname: return None
    path = os.path.join(base_dir, fname)
    if not os.path.exists(path): return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def b64video(fname):
    path = os.path.join(base_dir, fname)
    if not os.path.exists(path): return ""
    print(f"Embedding video: {fname}...")
    with open(path, "rb") as f:
        return f"data:video/mp4;base64,{base64.b64encode(f.read()).decode()}"

logo_b64 = b64img("logo nova_transparent.png") or b64img("logo nova.png")
video_b64_uri = b64video("video_back.mp4")

# --- TEAM CARDS ---
LI_SVG = '<svg viewBox="0 0 24 24" fill="white" width="17" height="17"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>'

cards_html = ""
for nome, arq, cargo, li in fotos:
    b64 = b64img(arq)
    src = f"data:image/{'png' if arq.endswith('.png') else 'jpeg'};base64,{b64}" if b64 else ""
    if not src:
        parts = nome.split()
        initials = (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200"><rect width="200" height="200" fill="#0d6efd"/><text x="100" y="118" font-family="Inter,Arial" font-size="80" font-weight="800" fill="white" text-anchor="middle">{initials}</text></svg>'''
        src = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
    cards_html += f'''
      <div class="team-card">
        <div class="team-photo-wrap">
          <img src="{src}" alt="{nome}" class="team-photo" />
          <div class="team-overlay">
            <a href="{li}" target="_blank" rel="noopener" class="li-link" title="LinkedIn">{LI_SVG}<span>LinkedIn</span></a>
          </div>
        </div>
        <div class="team-info">
          <div class="team-name">{nome}</div>
          <div class="team-role">{cargo}</div>
        </div>
      </div>'''

# --- HTML TEMPLATE ---
HTML = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Nautilus — Manutenção Preditiva Offshore</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet" />
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --navy:      #040d1a;
      --navy-dark: #020810;
      --blue:      #0d6efd;
      --cyan:      #4dc3ff;
      --cyan-dim:  rgba(77,195,255,0.12);
      --white:     #f0f6ff;
      --muted:     #8aa3c0;
      --border:    rgba(77,195,255,0.16);
      --card-bg:   rgba(10,31,58,0.85);
      --section-alt: #050e1e;
      --radius:    14px;
      --glow:      0 0 40px rgba(77,195,255,0.10);
    }}
    html {{ scroll-behavior: smooth; }}
    body {{ background: var(--navy); color: var(--white); font-family: 'Inter', sans-serif; line-height: 1.7; overflow-x: hidden; }}
    ::-webkit-scrollbar {{ width: 5px; }}
    ::-webkit-scrollbar-thumb {{ background: var(--cyan); border-radius: 3px; }}

    nav {{
      position: fixed; top: 0; left: 0; right: 0; z-index: 100;
      display: flex; align-items: center; justify-content: space-between;
      padding: 0 6%; height: 68px; background: rgba(4,13,26,0.82); backdrop-filter: blur(20px);
      border-bottom: 1px solid var(--border);
    }}
    .nav-logo {{ display: flex; align-items: center; gap: 12px; text-decoration: none; }}
    .nav-logo img {{ height: 44px; width: auto; filter: brightness(0) invert(1); }}
    .nav-logo span {{ font-weight: 800; font-size: 1.25rem; color: var(--white); }}
    .nav-links {{ display: flex; gap: 36px; list-style: none; }}
    .nav-links a {{ color: var(--muted); text-decoration: none; font-size: .875rem; font-weight: 500; transition: color .2s; }}
    .nav-links a:hover {{ color: var(--cyan); }}
    .nav-cta {{ background: linear-gradient(135deg, #0d6efd, #0a9ef0); color: #fff; padding: 10px 24px; border-radius: 8px; font-size: .875rem; font-weight: 700; text-decoration: none; box-shadow: 0 4px 15px rgba(13,110,253,0.3); }}

    #hero {{
      min-height: 100vh; display: flex; flex-direction: column; 
      align-items: flex-start; justify-content: center;
      text-align: left; padding: 0 10%; position: relative; overflow: hidden;
    }}
    .video-container {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: -1; }}
    .video-container video {{
      min-width: 100%; min-height: 100%; width: auto; height: auto;
      position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
      object-fit: cover; opacity: 0.75; filter: brightness(0.95);
    }}
    .hero-overlay {{
      position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 0;
      background: linear-gradient(90deg, var(--navy) 10%, transparent 60%, transparent 100%),
                  rgba(4, 13, 26, 0.25); 
    }}
    .hero-content {{ position: relative; z-index: 1; max-width: 550px; }}
    .hero-badge {{
      display: inline-flex; align-items: center; gap: 8px;
      background: var(--cyan-dim); border: 1px solid var(--border);
      color: var(--cyan); border-radius: 50px; padding: 5px 16px;
      font-size: .7rem; font-weight: 700; letter-spacing: 1px;
      text-transform: uppercase; margin-bottom: 24px;
    }}
    .hero-badge .dot {{ width: 6px; height: 6px; border-radius: 50%; background: var(--cyan); animation: pulse-dot 2s infinite; }}
    @keyframes pulse-dot {{ 0%,100%{{opacity:1;transform:scale(1)}} 50%{{opacity:.35;transform:scale(1.5)}} }}
    h1 {{
      font-size: clamp(2rem, 5vw, 3.2rem); font-weight: 900; line-height: 1.1; 
      background: linear-gradient(140deg, #ffffff 0%, #c2dcf8 45%, #4dc3ff 100%);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
      margin-bottom: 20px; text-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }}
    .hero-sub {{ font-size: clamp(0.9rem, 1.5vw, 1.05rem); color: var(--white); opacity: 0.95; max-width: 480px; margin-bottom: 36px; line-height: 1.6; }}
    .hero-buttons {{ display: flex; gap: 14px; }}
    .btn-primary {{ 
        background: linear-gradient(135deg, #0d6efd, #0a9ef0); 
        color: #fff; padding: 14px 32px; border-radius: 8px; 
        font-size: 1rem; font-weight: 800; text-decoration: none; 
        box-shadow: 0 8px 25px rgba(13,110,253,0.4); 
        transition: transform .2s, box-shadow .2s;
    }}
    .btn-primary:hover {{ transform: translateY(-2px); box-shadow: 0 12px 30px rgba(13,110,253,0.6); }}
    
    .btn-outline {{ border: 1.8px solid var(--white); color: var(--white); padding: 14px 32px; border-radius: 8px; font-size: 1rem; font-weight: 700; text-decoration: none; background: rgba(255,255,255,0.05); backdrop-filter: blur(10px); }}

    section {{ padding: 100px 6%; }}
    section.alt {{ background: var(--section-alt); }}
    .section-tag {{ display: inline-block; color: var(--cyan); font-size: .72rem; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 14px; }}
    h2 {{ font-size: clamp(1.8rem, 3.5vw, 2.5rem); font-weight: 800; line-height: 1.18; margin-bottom: 36px; }}

    /* SOBRE */
    #sobre .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 64px; align-items: center; }}
    @media(max-width:768px){{ #sobre .two-col {{ grid-template-columns: 1fr; }} }}
    .sobre-copy p {{ color: var(--muted); margin-bottom: 20px; line-height: 1.75; }}
    .info-card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: var(--radius); padding: 36px; box-shadow: var(--glow); }}
    .info-card h3 {{ font-size: 1rem; color: var(--cyan); margin-bottom: 20px; font-weight: 700; }}
    .info-list {{ list-style: none; display: flex; flex-direction: column; gap: 18px; }}
    .info-item {{ display: flex; gap: 14px; align-items: flex-start; }}
    .info-icon {{ font-size: 1.5rem; flex-shrink: 0; }}
    .info-title {{ font-size: .95rem; font-weight: 700; color: var(--white); }}
    .info-desc {{ font-size: .82rem; color: var(--muted); }}

    /* MVV */
    .mvv-grid {{ display: grid; grid-template-columns: repeat(3,1fr); gap: 24px; margin-top: 52px; }}
    @media(max-width:900px){{ .mvv-grid {{ grid-template-columns: 1fr; }} }}
    .mvv-card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: var(--radius); padding: 32px; box-shadow: var(--glow); position: relative; overflow: hidden; }}
    .mvv-card::before {{ content:''; position: absolute; top: 0; left: 0; right: 0; height: 3px; }}
    .mvv-card.missao::before {{ background: #0d6efd; }}
    .mvv-card.visao::before  {{ background: #22d3a5; }}
    .mvv-card.valores::before{{ background: #ffc145; }}
    .mvv-icon {{ font-size: 2rem; margin-bottom: 18px; }}
    .mvv-card h3 {{ font-size: 1.1rem; font-weight: 800; margin-bottom: 12px; }}
    .mvv-card p {{ font-size: .88rem; color: var(--muted); line-height: 1.6; }}
    .mvv-subtitle {{ margin-top: 18px; font-size: .72rem; color: rgba(138,163,192,0.6); font-style: italic; border-top: 1px solid var(--border); padding-top: 14px; }}

    /* RFID & DIFERENCIAIS */
    .grid-standard {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 24px; margin-top: 40px; }}
    .standard-card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: var(--radius); padding: 30px; transition: transform .3s; }}
    .standard-card:hover {{ transform: translateY(-5px); border-color: var(--cyan); }}
    .card-icon {{ font-size: 2rem; margin-bottom: 16px; }}
    .card-title {{ font-size: 1rem; font-weight: 700; margin-bottom: 10px; }}
    .card-text {{ font-size: .86rem; color: var(--muted); }}

    /* TEAM */
    #equipe {{ text-align: center; }}
    .team-grid {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 28px; margin-top: 52px; }}
    .team-card {{ flex: 1; min-width: 250px; max-width: 280px; background: var(--card-bg); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; text-align: left; }}
    .team-photo-wrap {{ position: relative; width: 100%; padding-top: 100%; overflow: hidden; }}
    .team-photo {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; transition: transform .4s; filter: grayscale(20%); }}
    .team-card:hover .team-photo {{ transform: scale(1.05); filter: grayscale(0); }}
    .team-overlay {{ position: absolute; inset: 0; background: linear-gradient(180deg, transparent 40%, rgba(4,13,26,0.95) 100%); display: flex; align-items: flex-end; justify-content: center; padding-bottom: 18px; opacity: 0; transition: opacity .35s; }}
    .team-card:hover .team-overlay {{ opacity: 1; }}
    .li-link {{ display: inline-flex; align-items: center; gap: 8px; background: #0A66C2; color: white; padding: 7px 16px; border-radius: 6px; text-decoration: none; font-size: .75rem; font-weight: 700; }}
    .team-info {{ padding: 18px; }}
    .team-name {{ font-size: 1rem; font-weight: 700; }}
    .team-role {{ font-size: .75rem; color: var(--muted); margin-top: 6px; min-height: 2.8em; line-height: 1.4; }}

    footer {{ background: var(--navy-dark); border-top: 1px solid var(--border); padding: 40px 6% 25px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px; }}
    .footer-brand {{ display: flex; align-items: center; gap: 10px; font-weight: 800; color: var(--cyan); text-decoration: none; }}
    .footer-brand img {{ height: 30px; width: auto; filter: brightness(0) invert(1); }}
    .footer-copy {{ font-size: .75rem; color: var(--muted); }}

    .aos {{ opacity: 0; transform: translateY(20px); transition: opacity .6s ease, transform .6s ease; }}
    .aos.visible {{ opacity: 1; transform: none; }}
  </style>
</head>
<body>

<nav>
  <a href="#hero" class="nav-logo"><img src="data:image/png;base64,{logo_b64}" alt="Logo" /><span>Nautilus</span></a>
  <ul class="nav-links">
    <li><a href="#sobre">Início</a></li>
    <li><a href="#rfid">Tecnologia</a></li>
    <li><a href="#mvv">Propósito</a></li>
    <li><a href="#equipe">Equipe</a></li>
  </ul>
  <a href="https://prio-nautilus.streamlit.app/" class="nav-cta" target="_blank">🚀 ACESSAR DASHBOARD</a>
</nav>

<section id="hero">
  <div class="video-container">
    <video autoplay muted loop playsinline><source src="{video_b64_uri}" type="video/mp4"></video>
    <div class="hero-overlay"></div>
  </div>
  <div class="hero-content">
    <div class="hero-badge aos"><span class="dot"></span> Monitoramento Offshore 24/7</div>
    <h1 class="aos">Inteligência Preditiva<br/>Nautilus</h1>
    <p class="hero-sub aos">Soluções integradas de manutenção técnica e gestão inteligente para garantir a máxima disponibilidade operacional de ativos offshore.</p>
    <div class="hero-buttons aos">
      <a href="https://prio-nautilus.streamlit.app/" class="btn-primary" target="_blank">🚀 ACESSAR DASHBOARD</a>
      <a href="#sobre" class="btn-outline">Saiba Mais</a>
    </div>
  </div>
</section>

<!-- SOBRE -->
<section id="sobre" class="alt">
  <div class="two-col">
    <div class="sobre-copy aos">
      <span class="section-tag">Quem Somos</span>
      <h2>Uma empresa construída sobre confiabilidade</h2>
      <p>O <strong>Nautilus</strong> é especializado em soluções de manutenção preditiva para a indústria de óleo e gás offshore. Nossa plataforma opera nos ambientes mais exigentes, garantindo disponibilidade mesmo em condições extremas.</p>
    </div>
    <div class="aos">
      <div class="info-card">
        <h3>⚙️ Capacidades Principais</h3>
        <ul class="info-list">
          <li class="info-item"><span class="info-icon">📡</span><div><div class="info-title">Sensoriamento RFID</div><div class="info-desc">Vibração e temperatura sem cabos ou redes externas.</div></div></li>
          <li class="info-item"><span class="info-icon">🤖</span><div><div class="info-title">Motor de IA Local</div><div class="info-desc">Assistente LLM embarcado operável sem internet.</div></div></li>
          <li class="info-item"><span class="info-icon">🗺️</span><div><div class="info-title">Mapa 3D</div><div class="info-desc">Visualização tridimensional interativa dos ativos.</div></div></li>
        </ul>
      </div>
    </div>
  </div>
</section>

<!-- TECNOLOGIA RFID -->
<section id="rfid">
  <span class="section-tag">Tecnologia Proprietária</span>
  <h2>Sensoriamento IoT + RFID Industrial</h2>
  <div class="grid-standard aos">
    <div class="standard-card"><div class="card-icon">🏷️</div><div class="card-title">Tags RFID</div><div class="card-text">Identificação única e rastreabilidade individual de ativos.</div></div>
    <div class="standard-card"><div class="card-icon">📶</div><div class="card-title">Coleta em Campo</div><div class="card-text">Rondas rápidas sem digitação manual, eliminando erros humanos.</div></div>
    <div class="standard-card"><div class="card-icon">📊</div><div class="card-title">Análise Preditiva</div><div class="card-text">Algoritmos que calculam prazos de intervenção antes da falha.</div></div>
    <div class="standard-card"><div class="card-icon">🔒</div><div class="card-title">Segurança Air‑Gapped</div><div class="card-text">Opera 100% offline. Nenhum dado sensível sai da instalação.</div></div>
  </div>
</section>

<!-- MVV -->
<section id="mvv" class="alt">
  <div style="max-width:640px"><span class="section-tag">Propósito</span><h2>Missão, Visão e Valores</h2></div>
  <div class="mvv-grid">
    <div class="mvv-card missao aos">
      <div class="mvv-icon">🐚</div><h3>Missão</h3>
      <p>Garantir a máxima disponibilidade operacional por meio de soluções integradas de manutenção técnica e gestão inteligente.</p>
    </div>
    <div class="mvv-card visao aos">
      <div class="mvv-icon">🏮</div><h3>Visão</h3>
      <p>Ser a referência em gestão de ativos e manutenção industrial no setor offshore brasileiro até 2030.</p>
    </div>
    <div class="mvv-card valores aos">
      <div class="mvv-icon">🌊</div><h3>Valores</h3>
      <p>Segurança operacional, Excelência técnica, Transparência, Inovação contínua e Trabalho colaborativo.</p>
    </div>
  </div>
</section>

<!-- EQUIPE -->
<section id="equipe" class="alt">
  <span class="section-tag">Pessoas</span><h2>Nossa Equipe</h2>
  <div class="team-grid aos">{cards_html}</div>
</section>

<footer>
  <a href="#" class="footer-brand"><img src="data:image/png;base64,{logo_b64}" alt="Logo" />Nautilus</a>
  <div class="footer-copy">© 2026 Nautilus · Todos os direitos reservados</div>
</footer>

<script>
  const obs = new IntersectionObserver(entries => {{
    entries.forEach(e => {{ if (e.isIntersecting) e.target.classList.add('visible'); }});
  }}, {{ threshold: 0.1 }});
  document.querySelectorAll('.aos').forEach(el => obs.observe(el));
</script>
</body>
</html>"""

with open(out_path, "w", encoding="utf-8") as f:
    f.write(HTML)
print("Gerado com sucesso (Self-Contained Video Embedded).")
