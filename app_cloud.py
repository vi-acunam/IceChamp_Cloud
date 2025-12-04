from flask import Flask, request, jsonify, render_template_string
import os
from supabase import create_client
import time

app = Flask(__name__)

# --- CONFIGURACIÓN (Las leeremos del servidor) ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Si no hay configuración, no podemos arrancar
if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Faltan variables de entorno SUPABASE_URL y SUPABASE_KEY")
    client = None
else:
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- PLANTILLA HTML (Diseño oscuro moderno) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Inscripción IceChamp</title>
    <style>
        body { background: #121212; color: white; font-family: sans-serif; display: flex; flex-direction: column; align-items: center; padding: 20px; }
        h1 { color: #f1c40f; text-transform: uppercase; }
        .card { background: #1e1e1e; padding: 20px; border-radius: 10px; width: 100%; max-width: 400px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        input { width: 100%; padding: 12px; margin: 10px 0; background: #333; border: 1px solid #444; color: white; border-radius: 5px; box-sizing: border-box;}
        button { width: 100%; padding: 15px; background: #f1c40f; color: black; font-weight: bold; border: none; border-radius: 5px; cursor: pointer; margin-top: 10px;}
        .msg { color: #2ecc71; text-align: center; margin-top: 10px; display: none; }
        .error { color: #e74c3c; text-align: center; margin-top: 10px; display: none; }
        label { font-size: 0.9rem; color: #aaa; }
    </style>
</head>
<body>
    <h1>🏆 Inscripción Torneo</h1>
    <div class="card">
        <label>Nombre del Jugador</label>
        <input type="text" id="name" placeholder="Ej: Juan Pérez">
        
        <label>Club (Opcional)</label>
        <input type="text" id="club" placeholder="Ej: Leones TC">
        
        <label>Categoría</label>
        <input type="text" id="category" placeholder="Ej: Todo Competidor">

        <label>Foto de Perfil (Opcional)</label>
        <input type="file" id="photo" accept="image/*">

        <button onclick="register()" id="btn">CONFIRMAR INSCRIPCIÓN</button>
        <div class="msg" id="msg">¡Inscripción exitosa!</div>
        <div class="error" id="err"></div>
    </div>

    <div style="margin-top: 30px;">
        <a href="/ranking" style="color: #f1c40f; text-decoration: none;">Ver Ranking ELO Histórico &rarr;</a>
    </div>

    <script>
        async function register() {
            let btn = document.getElementById('btn');
            let msg = document.getElementById('msg');
            let err = document.getElementById('err');
            
            let name = document.getElementById('name').value;
            let club = document.getElementById('club').value;
            let cat = document.getElementById('category').value;
            let fileInput = document.getElementById('photo');

            if(!name || !cat) { err.innerText = "Nombre y Categoría obligatorios"; err.style.display = "block"; return; }

            btn.disabled = true; btn.innerText = "Enviando...";
            err.style.display = "none";

            let formData = new FormData();
            formData.append('name', name);
            formData.append('club', club);
            formData.append('category', cat);
            if(fileInput.files[0]) {
                formData.append('file', fileInput.files[0]);
            }

            try {
                let r = await fetch('/api/submit', { method: 'POST', body: formData });
                let data = await r.json();
                
                if(data.status === 'ok') {
                    msg.style.display = "block";
                    btn.innerText = "¡Listo!";
                    setTimeout(() => location.reload(), 2000);
                } else {
                    throw new Error(data.msg);
                }
            } catch(e) {
                err.innerText = "Error: " + e.message;
                err.style.display = "block";
                btn.disabled = false; btn.innerText = "CONFIRMAR INSCRIPCIÓN";
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/ranking')
def ranking_view():
    # Vista simple de Ranking JSON (puedes mejorarla con HTML si quieres)
    if not client: return "Error config", 500
    res = client.table('players').select('name, club, rating, category').order('rating', desc=True).execute()
    return jsonify(res.data)

@app.route('/api/submit', methods=['POST'])
def api_submit():
    if not client: return jsonify({'status': 'error', 'msg': 'Server misconfigured'}), 500
    
    name = request.form.get('name')
    club = request.form.get('club', '')
    category = request.form.get('category', 'General')
    file = request.files.get('file')

    photo_url = ""

    # 1. Subir Foto a Supabase Storage (Bucket 'photos')
    if file:
        try:
            # Limpiamos nombre de archivo
            ext = file.filename.split('.')[-1]
            filename = f"{int(time.time())}_{name.replace(' ', '_')}.{ext}"
            file_bytes = file.read()
            
            # Subida al bucket 'photos'
            # NOTA: Debes crear el bucket 'photos' en tu panel de Supabase y hacerlo público.
            res = client.storage.from_("photos").upload(path=filename, file=file_bytes, file_options={"content-type": file.content_type})
            
            # Obtener URL pública
            public_url_data = client.storage.from_("photos").get_public_url(filename)
            # Dependiendo de la versión de la librería, get_public_url devuelve string o dict.
            # Ajusta si es necesario. Generalmente devuelve la URL directa.
            photo_url = public_url_data 
            
        except Exception as e:
            print(f"Error subiendo foto: {e}")
            # No fallamos la inscripción si falla la foto, solo seguimos sin foto.

    # 2. Guardar en Base de Datos (Tabla 'inscriptions')
    try:
        data = {
            "player_name": name,
            "club": club,
            "category": category,
            "photo_url": photo_url # Guardamos la URL de la nube
        }
        client.table('inscriptions').insert(data).execute()
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)
