import os
import json
import requests
import logging
from flask import Flask, request, jsonify
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime
import tempfile
import base64

# Carrega variáveis de ambiente
load_dotenv()

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicializa Flask
app = Flask(__name__)

# Configurações
Z_API_TOKEN = os.getenv('Z_API_TOKEN')
Z_API_INSTANCE = os.getenv('Z_API_INSTANCE')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
Z_API_BASE_URL = "https://api.z-api.io"

# Inicializa cliente Groq
groq_client = Groq(api_key=GROQ_API_KEY)

# Dicionário para manter contexto básico das conversas
conversation_context = {}

# Prompt da Lina
LINA_PROMPT = """NOME: Lina

INTRODUÇÃO INICIAL:
Se for a primeira mensagem do usuário, responda exatamente:
"Oi! Eu sou a Lina 😊 Posso te ajudar com qualquer assunto - desde receitas e tecnologia até estudos e relacionamentos. O que você precisa hoje?"

IDENTIDADE:
- Assistente versátil e inteligente
- Especialista generalista com conhecimento profundo em múltiplas áreas
- Personalidade acolhedora, prática e confiável

ÁREAS DE EXPERTISE:
• Vida Prática: Culinária, organização, finanças pessoais, DIY
• Tecnologia: Programação, IA, segurança digital, tendências tech
• Bem-estar: Saúde física e mental, exercícios, nutrição, mindfulness
• Educação: Técnicas de estudo, explicações didáticas, orientação acadêmica
• Carreira: Desenvolvimento profissional, empreendedorismo, produtividade
• Relacionamentos: Comunicação, resolução de conflitos, inteligência emocional
• Cultura & Lazer: Arte, música, literatura, viagens, hobbies
• Ciências: Explicações científicas acessíveis, curiosidades, inovações
• Atualidades: Análise contextualizada de eventos e tendências

DIRETRIZES DE RESPOSTA:
1. ESCUTE primeiro - identifique a real necessidade por trás da pergunta
2. PERSONALIZE - ajuste tom e profundidade conforme o contexto
3. SEJA PRÁTICA - forneça passos acionáveis e exemplos concretos
4. ESTRUTURE - use formatação clara quando apropriado
5. VALIDE - reconheça sentimentos e preocupações quando relevante

PRINCÍPIOS:
- Honestidade: "Não tenho certeza sobre isso, mas posso pesquisar" ou "Isso está fora da minha área, mas posso sugerir..."
- Empatia: Reconheça o contexto emocional das perguntas
- Clareza: Evite jargões desnecessários, explique termos técnicos
- Proatividade: Antecipe perguntas relacionadas e ofereça recursos extras
- Segurança: Sempre priorize o bem-estar do usuário em suas orientações

ESTILO DE COMUNICAÇÃO:
- Amigável sem ser invasiva
- Profissional sem ser distante
- Entusiasmada sem exageros
- Use emojis com moderação para dar leveza (1-2 por resposta no máximo)
- Varie entre respostas curtas e detalhadas conforme a necessidade

CASOS ESPECIAIS:
- Urgências: Seja direta e rápida, foque no essencial
- Aprendizado: Use analogias e divida conceitos complexos
- Criatividade: Inspire com múltiplas perspectivas e ideias
- Problemas pessoais: Ouça com empatia, sugira sem impor"""

def send_message_to_whatsapp(phone, message):
    """Envia mensagem de texto via Z-API"""
    try:
        url = f"{Z_API_BASE_URL}/instances/{Z_API_INSTANCE}/token/{Z_API_TOKEN}/send-text"
        
        payload = {
            "phone": phone,
            "message": message
        }
        
        headers = {
            "Content-Type": "application/json",
            "Client-Token": Z_API_TOKEN
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        logger.info(f"Mensagem enviada para {phone}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem: {str(e)}")
        return False

def download_audio_from_z_api(audio_id):
    """Baixa arquivo de áudio do Z-API"""
    try:
        url = f"{Z_API_BASE_URL}/instances/{Z_API_INSTANCE}/token/{Z_API_TOKEN}/download-media"
        
        params = {
            "messageId": audio_id
        }
        
        headers = {
            "Client-Token": Z_API_TOKEN
        }
        
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        
        # O Z-API retorna o áudio em base64
        audio_data = response.json()
        if 'base64' in audio_data:
            return base64.b64decode(audio_data['base64'])
        
        return None
        
    except Exception as e:
        logger.error(f"Erro ao baixar áudio: {str(e)}")
        return None

def transcribe_audio(audio_data):
    """Transcreve áudio usando Whisper da Groq"""
    try:
        # Salva temporariamente o arquivo de áudio
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_audio:
            temp_audio.write(audio_data)
            temp_audio_path = temp_audio.name
        
        # Transcreve com Whisper
        with open(temp_audio_path, "rb") as audio_file:
            transcription = groq_client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=audio_file,
                language="pt"
            )
        
        # Remove arquivo temporário
        os.unlink(temp_audio_path)
        
        return transcription.text
        
    except Exception as e:
        logger.error(f"Erro na transcrição: {str(e)}")
        return None

def get_lina_response(user_message, phone_number):
    """Gera resposta da Lina usando Groq"""
    try:
        # Verifica se é primeira mensagem do usuário
        is_first_message = phone_number not in conversation_context
        
        # Inicializa ou recupera contexto
        if is_first_message:
            conversation_context[phone_number] = {
                "messages": [],
                "created_at": datetime.now().isoformat()
            }
        
        context = conversation_context[phone_number]
        
        # Prepara mensagens para o modelo
        messages = [
            {"role": "system", "content": LINA_PROMPT}
        ]
        
        # Adiciona histórico recente (últimas 5 interações)
        for msg in context["messages"][-10:]:  # Últimas 5 trocas (user + assistant)
            messages.append(msg)
        
        # Adiciona mensagem atual
        messages.append({"role": "user", "content": user_message})
        
        # Gera resposta com Groq
        response = groq_client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        lina_response = response.choices[0].message.content
        
        # Atualiza contexto
        context["messages"].append({"role": "user", "content": user_message})
        context["messages"].append({"role": "assistant", "content": lina_response})
        
        # Limita tamanho do histórico
        if len(context["messages"]) > 20:
            context["messages"] = context["messages"][-20:]
        
        return lina_response
        
    except Exception as e:
        logger.error(f"Erro ao gerar resposta: {str(e)}")
        return "Ops! 😅 Tive um pequeno problema técnico. Pode repetir sua mensagem?"

@app.route('/webhook', methods=['POST'])
def webhook():
    """Endpoint principal do webhook Z-API"""
    try:
        # Log do payload recebido
        data = request.get_json()
        logger.info(f"Webhook recebido: {json.dumps(data, indent=2)}")
        
        # Verifica se é mensagem recebida
        if not data or data.get('type') != 'ReceivedCallback':
            return jsonify({"status": "ignored"}), 200
        
        # Extrai informações da mensagem
        phone = data.get('phone')
        message_type = data.get('messageType')
        
        if not phone:
            logger.warning("Mensagem sem número de telefone")
            return jsonify({"status": "error", "message": "No phone number"}), 400
        
        user_message = None
        
        # Processa mensagem de texto
        if message_type == 'text':
            user_message = data.get('text', {}).get('message', '')
            logger.info(f"Mensagem de texto de {phone}: {user_message}")
        
        # Processa mensagem de áudio
        elif message_type in ['audio', 'ptt']:
            logger.info(f"Áudio recebido de {phone}")
            
            # Obtém ID do áudio
            audio_info = data.get('audio', {}) or data.get('ptt', {})
            audio_id = audio_info.get('messageId')
            
            if audio_id:
                # Baixa e transcreve áudio
                audio_data = download_audio_from_z_api(audio_id)
                if audio_data:
                    transcription = transcribe_audio(audio_data)
                    if transcription:
                        user_message = transcription
                        logger.info(f"Transcrição: {transcription}")
                        
                        # Envia confirmação da transcrição
                        send_message_to_whatsapp(
                            phone, 
                            f"🎤 *Entendi seu áudio:* _{transcription}_"
                        )
                    else:
                        send_message_to_whatsapp(
                            phone,
                            "Desculpe, não consegui entender o áudio. Pode tentar novamente? 🎤"
                        )
                        return jsonify({"status": "error"}), 200
        
        # Se não há mensagem para processar, ignora
        if not user_message or not user_message.strip():
            return jsonify({"status": "ignored"}), 200
        
        # Gera resposta da Lina
        logger.info(f"Gerando resposta para: {user_message}")
        lina_response = get_lina_response(user_message, phone)
        
        # Envia resposta
        if send_message_to_whatsapp(phone, lina_response):
            logger.info(f"Resposta enviada para {phone}")
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"status": "error"}), 500
        
    except Exception as e:
        logger.error(f"Erro no webhook: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de health check"""
    return jsonify({
        "status": "healthy",
        "service": "Lina WhatsApp Agent",
        "timestamp": datetime.now().isoformat(),
        "environment": {
            "z_api_configured": bool(Z_API_TOKEN and Z_API_INSTANCE),
            "groq_configured": bool(GROQ_API_KEY)
        }
    }), 200

@app.route('/', methods=['GET'])
def home():
    """Página inicial"""
    return jsonify({
        "agent": "Lina",
        "version": "1.0",
        "status": "online",
        "endpoints": {
            "webhook": "/webhook",
            "health": "/health"
        }
    }), 200

if __name__ == '__main__':
    # Verifica configurações essenciais
    if not all([Z_API_TOKEN, Z_API_INSTANCE, GROQ_API_KEY]):
        logger.error("Variáveis de ambiente não configuradas!")
        exit(1)
    
    logger.info("Lina WhatsApp Agent iniciado!")
    logger.info(f"Z-API Instance: {Z_API_INSTANCE}")
    
    # Inicia servidor
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
