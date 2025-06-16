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

# Verifica se as variáveis estão configuradas
if not all([Z_API_TOKEN, Z_API_INSTANCE, GROQ_API_KEY]):
    logger.error("ERRO: Variáveis de ambiente não configuradas!")
    logger.error(f"Z_API_TOKEN: {'✓' if Z_API_TOKEN else '✗'}")
    logger.error(f"Z_API_INSTANCE: {'✓' if Z_API_INSTANCE else '✗'}")
    logger.error(f"GROQ_API_KEY: {'✓' if GROQ_API_KEY else '✗'}")

# Inicializa cliente Groq (SEM parâmetros extras)
try:
    groq_client = Groq(api_key=GROQ_API_KEY)
    logger.info("✅ Cliente Groq inicializado com sucesso")
except Exception as e:
    logger.error(f"❌ Erro ao inicializar Groq: {str(e)}")
    groq_client = None

# Dicionário para manter contexto básico das conversas
conversation_context = {}

# Prompt da Lina
LINA_PROMPT = """NOME: Lina

INTRODUÇÃO INICIAL:
Se for a primeira mensagem do usuário, responda exatamente:
"Hey! Lina na área 🚀 Considere seus problemas resolvidos (ou pelo menos, vamos tentar juntos!). O que tá rolando hoje?"

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
        # URL direta para garantir que está correta
        url = f"https://api.z-api.io/instances/{Z_API_INSTANCE}/token/{Z_API_TOKEN}/send-text"
        
        payload = {
            "phone": phone,
            "message": message
        }
        
        headers = {
            "Content-Type": "application/json",
            "Client-Token": Z_API_TOKEN
        }
        
        logger.info(f"📤 Enviando para {phone}: {message[:50]}...")
        logger.info(f"🔗 URL: {url}")
        logger.info(f"📦 Payload: {payload}")
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        logger.info(f"📊 Status Code: {response.status_code}")
        logger.info(f"📝 Response: {response.text}")
        
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"✅ Z-API Response: {result}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao enviar mensagem para {phone}: {str(e)}")
        return False

def download_audio_from_z_api(message_id):
    """Baixa arquivo de áudio do Z-API"""
    try:
        urls = [
            f"{Z_API_BASE_URL}/instances/{Z_API_INSTANCE}/token/{Z_API_TOKEN}/download-media/{message_id}",
            f"{Z_API_BASE_URL}/instances/{Z_API_INSTANCE}/token/{Z_API_TOKEN}/download-media"
        ]
        
        headers = {
            "Client-Token": Z_API_TOKEN
        }
        
        for url in urls:
            try:
                if "download-media/" in url:
                    response = requests.get(url, headers=headers, timeout=30)
                else:
                    params = {"messageId": message_id}
                    response = requests.get(url, params=params, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"🔍 Download response: {data}")
                    
                    if 'base64' in data:
                        return base64.b64decode(data['base64'])
                    elif 'media' in data and 'base64' in data['media']:
                        return base64.b64decode(data['media']['base64'])
                    elif 'file' in data:
                        file_response = requests.get(data['file'], timeout=30)
                        return file_response.content
                        
            except Exception as e:
                logger.warning(f"⚠️ Download attempt failed: {str(e)}")
                continue
        
        logger.error("❌ All download attempts failed")
        return None
        
    except Exception as e:
        logger.error(f"❌ Error downloading audio: {str(e)}")
        return None

def transcribe_audio(audio_data):
    """Transcreve áudio usando Whisper da Groq"""
    try:
        if not groq_client:
            logger.error("❌ Groq client not initialized")
            return None
            
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_audio:
            temp_audio.write(audio_data)
            temp_audio_path = temp_audio.name
        
        logger.info(f"🎤 Transcribing audio: {temp_audio_path}")
        
        with open(temp_audio_path, "rb") as audio_file:
            transcription = groq_client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=audio_file,
                language="pt"
            )
        
        os.unlink(temp_audio_path)
        
        transcription_text = transcription.text.strip()
        logger.info(f"✅ Transcription: {transcription_text}")
        return transcription_text
        
    except Exception as e:
        logger.error(f"❌ Transcription error: {str(e)}")
        try:
            if 'temp_audio_path' in locals():
                os.unlink(temp_audio_path)
        except:
            pass
        return None

def get_lina_response(user_message, phone_number):
    """Gera resposta da Lina usando Groq"""
    try:
        if not groq_client:
            return "Desculpe, estou com problemas técnicos no momento. Tente novamente em alguns minutos! 😅"
            
        # Verifica se é primeira mensagem do usuário
        is_first_message = phone_number not in conversation_context
        
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
        
        # Adiciona histórico recente
        for msg in context["messages"][-10:]:
            messages.append(msg)
        
        # Adiciona mensagem atual
        messages.append({"role": "user", "content": user_message})
        
        logger.info(f"🧠 Generating response with Groq for: {user_message[:50]}...")
        
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
        
        logger.info(f"✅ Response generated: {lina_response[:100]}...")
        return lina_response
        
    except Exception as e:
        logger.error(f"❌ Error generating response: {str(e)}")
        return "Ops! 😅 Tive um pequeno problema técnico. Pode repetir sua mensagem?"

@app.route('/webhook', methods=['POST'])
def webhook():
    """Endpoint principal do webhook Z-API"""
    try:
        data = request.get_json()
        logger.info(f"📥 Webhook received: {json.dumps(data, indent=2)}")
        
        if not data:
            logger.warning("⚠️ Empty payload received")
            return jsonify({"status": "ignored"}), 200
        
        # Verifica se é callback de mensagem recebida - MODO FLEXÍVEL
        message_type_field = data.get('type')
        logger.info(f"🔍 Message type field: {message_type_field}")
        
        # Aceita qualquer tipo de callback ou None
        if message_type_field and message_type_field not in ['ReceivedCallback', 'received']:
            logger.info(f"⏭️ Callback type ignored: {message_type_field}")
            return jsonify({"status": "ignored"}), 200
        
        # Extrai informações da mensagem
        phone = data.get('phone') or data.get('from')
        if not phone:
            logger.warning("⚠️ No phone number found")
            return jsonify({"status": "error", "message": "No phone number"}), 400
        
        # Corrige formato do número brasileiro (adiciona 9 se necessário)
        original_phone = phone
        if phone and phone.startswith('55') and len(phone) == 12:
            # Extrai: código país (55) + DDD (2 dígitos) + número (8 dígitos)
            # Formato: 55 + DD + 8dígitos → 55 + DD + 9 + 8dígitos
            codigo_pais = phone[:2]  # 55
            ddd = phone[2:4]         # DD (ex: 71, 11, 21, etc)
            numero = phone[4:]       # 8 dígitos
            
            # Monta com o 9
            phone = codigo_pais + ddd + '9' + numero
            logger.info(f"📱 Número corrigido de {original_phone} para {phone}")
        
        # Limpa número de telefone
        phone = phone.replace('+', '').replace('-', '').replace(' ', '')
        logger.info(f"📱 Processing message from: {phone}")
        
        user_message = None
        
        # PROCESSA TEXTO - Modo super flexível
        text_data = data.get('text', {})
        if text_data and isinstance(text_data, dict):
            user_message = text_data.get('message', '')
            logger.info(f"💬 Text message found: {user_message}")
        
        # Se ainda não achou a mensagem, procura em outros lugares
        if not user_message:
            # Verifica se a mensagem está diretamente no data
            user_message = data.get('message', '')
            if user_message:
                logger.info(f"💬 Direct message found: {user_message}")
        
        # PROCESSA ÁUDIO
        message_type = data.get('messageType', 'text')
        if message_type in ['audio', 'ptt'] and not user_message:
            logger.info(f"🎤 Audio message detected")
            
            audio_info = data.get('audio', {}) or data.get('ptt', {})
            message_id = audio_info.get('messageId') or data.get('messageId')
            
            if message_id:
                logger.info(f"🔍 Processing audio ID: {message_id}")
                
                audio_data = download_audio_from_z_api(message_id)
                if audio_data:
                    transcription = transcribe_audio(audio_data)
                    if transcription and transcription.strip():
                        user_message = transcription
                        logger.info(f"✅ Audio transcribed: {transcription}")
                        
                        send_message_to_whatsapp(
                            phone, 
                            f"🎤 *Entendi seu áudio:* _{transcription}_"
                        )
                    else:
                        send_message_to_whatsapp(
                            phone,
                            "Desculpe, não consegui entender o áudio. Pode tentar enviar uma mensagem de texto? 🎤"
                        )
                        return jsonify({"status": "transcription_failed"}), 200
                else:
                    send_message_to_whatsapp(
                        phone,
                        "Não consegui processar o áudio. Pode tentar novamente? 🎤"
                    )
                    return jsonify({"status": "download_failed"}), 200
        
        # Verifica se há mensagem para processar
        if not user_message or not user_message.strip():
            logger.warning(f"⚠️ Empty or invalid message. Raw data: {data}")
            return jsonify({"status": "ignored", "reason": "empty_message"}), 200
        
        # Gera resposta da Lina
        logger.info(f"🤖 Generating Lina response for: {user_message}")
        lina_response = get_lina_response(user_message, phone)
        
        # Envia resposta
        if send_message_to_whatsapp(phone, lina_response):
            logger.info(f"✅ Conversation completed successfully for {phone}")
            return jsonify({"status": "success"}), 200
        else:
            logger.error(f"❌ Failed to send response to {phone}")
            return jsonify({"status": "send_failed"}), 500
        
    except Exception as e:
        logger.error(f"💥 Webhook error: {str(e)}", exc_info=True)
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
            "groq_configured": bool(GROQ_API_KEY),
            "groq_client_ready": groq_client is not None
        },
        "active_conversations": len(conversation_context)
    }), 200

@app.route('/', methods=['GET'])
def home():
    """Página inicial"""
    return jsonify({
        "agent": "Lina - Assistente IA para WhatsApp",
        "version": "1.1",
        "status": "online" if groq_client else "partially_online",
        "endpoints": {
            "webhook": "/webhook",
            "health": "/health"
        },
        "features": [
            "Conversas por texto",
            "Transcrição de áudios",
            "Múltiplas áreas de conhecimento",
            "Contexto de conversa",
            "Processamento flexível de webhooks"
        ]
    }), 200

@app.route('/test', methods=['POST'])
def test_endpoint():
    """Endpoint para testar funcionalidades"""
    try:
        data = request.get_json()
        test_type = data.get('type', 'message')
        
        if test_type == 'message':
            message = data.get('message', 'Olá!')
            phone = data.get('phone', '5511999999999')
            
            response = get_lina_response(message, phone)
            return jsonify({
                "status": "success",
                "input": message,
                "output": response
            })
            
        elif test_type == 'health':
            return health_check()
            
        return jsonify({"status": "unknown_test_type"}), 400
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    logger.info("🤖 Lina WhatsApp Agent starting...")
    logger.info(f"📱 Z-API Instance: {Z_API_INSTANCE}")
    logger.info(f"🧠 Groq Client: {'✅ Ready' if groq_client else '❌ Error'}")
    
    port = int(os.getenv('PORT', 5000))
    logger.info(f"🚀 Server starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
