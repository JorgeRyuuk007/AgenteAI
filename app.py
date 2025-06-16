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

# Configurações Evolution API
EVOLUTION_API_URL = "https://evolution-api-v150.onrender.com"
EVOLUTION_INSTANCE = "lina"  # Nome da instância
EVOLUTION_API_KEY = "B6D711FCDE4D4FD5936544120E713976"  # API Key global
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# Verifica se as variáveis estão configuradas
if not GROQ_API_KEY:
    logger.error("ERRO: GROQ_API_KEY não configurada!")
else:
    logger.info("✅ Configurações carregadas com sucesso")

# Inicializa cliente Groq
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
    """Envia mensagem de texto via Evolution API"""
    try:
        url = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE}"
        
        payload = {
            "number": phone,
            "text": message
        }
        
        headers = {
            "Content-Type": "application/json",
            "apikey": EVOLUTION_API_KEY
        }
        
        logger.info(f"📤 Enviando para {phone}: {message[:50]}...")
        logger.info(f"🔗 URL: {url}")
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        logger.info(f"📊 Status Code: {response.status_code}")
        logger.info(f"📝 Response: {response.text}")
        
        if response.status_code == 201:
            result = response.json()
            logger.info(f"✅ Evolution API Response: {result}")
            return True
        else:
            logger.error(f"❌ Erro HTTP {response.status_code}: {response.text}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Erro ao enviar mensagem para {phone}: {str(e)}")
        return False

def download_audio_from_evolution(media_url):
    """Baixa arquivo de áudio via Evolution API"""
    try:
        headers = {
            "apikey": EVOLUTION_API_KEY
        }
        
        response = requests.get(media_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return response.content
        else:
            logger.error(f"❌ Erro ao baixar áudio: {response.status_code}")
            return None
        
    except Exception as e:
        logger.error(f"❌ Erro no download do áudio: {str(e)}")
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
    """Endpoint principal do webhook Evolution API"""
    try:
        data = request.get_json()
        logger.info(f"📥 Webhook received: {json.dumps(data, indent=2)}")
        
        if not data:
            logger.warning("⚠️ Empty payload received")
            return jsonify({"status": "ignored"}), 200
        
        # Estrutura da Evolution API
        event = data.get('event')
        instance = data.get('instance')
        data_content = data.get('data', {})
        
        # Verifica se é mensagem recebida
        if event != 'messages.upsert':
            logger.info(f"⏭️ Event ignored: {event}")
            return jsonify({"status": "ignored"}), 200
        
        # Verifica se a instância é a nossa
        if instance != EVOLUTION_INSTANCE:
            logger.info(f"⏭️ Instance ignored: {instance}")
            return jsonify({"status": "ignored"}), 200
        
        # Extrai informações da mensagem
        message_info = data_content
        if isinstance(message_info, list) and len(message_info) > 0:
            message_info = message_info[0]
        
        # Verifica se a mensagem é de entrada (não nossa)
        if message_info.get('key', {}).get('fromMe'):
            logger.info("⏭️ Message from bot ignored")
            return jsonify({"status": "ignored"}), 200
        
        # Extrai número do telefone
        remote_jid = message_info.get('key', {}).get('remoteJid', '')
        if not remote_jid:
            logger.warning("⚠️ No phone number found")
            return jsonify({"status": "error", "message": "No phone number"}), 400
        
        # Limpa número de telefone (remove @s.whatsapp.net)
        phone = remote_jid.replace('@s.whatsapp.net', '').replace('@c.us', '')
        logger.info(f"📱 Processing message from: {phone}")
        
        # Extrai conteúdo da mensagem
        message_content = message_info.get('message', {})
        user_message = None
        
        # PROCESSA TEXTO
        if 'conversation' in message_content:
            user_message = message_content['conversation']
            logger.info(f"💬 Text message: {user_message}")
        
        elif 'extendedTextMessage' in message_content:
            user_message = message_content['extendedTextMessage'].get('text', '')
            logger.info(f"💬 Extended text message: {user_message}")
        
        # PROCESSA ÁUDIO
        elif 'audioMessage' in message_content:
            logger.info("🎤 Audio message detected")
            audio_msg = message_content['audioMessage']
            
            # Tenta obter URL do áudio
            media_url = audio_msg.get('url')
            if media_url:
                audio_data = download_audio_from_evolution(media_url)
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
            logger.warning(f"⚠️ Empty or unsupported message type. Content: {message_content}")
            return jsonify({"status": "ignored", "reason": "unsupported_message"}), 200
        
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
        "api": "Evolution API",
        "environment": {
            "evolution_api_url": EVOLUTION_API_URL,
            "evolution_instance": EVOLUTION_INSTANCE,
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
        "version": "2.0 - Evolution API",
        "status": "online" if groq_client else "partially_online",
        "api": "Evolution API",
        "endpoints": {
            "webhook": "/webhook",
            "health": "/health"
        },
        "features": [
            "Conversas por texto",
            "Transcrição de áudios",
            "Múltiplas áreas de conhecimento",
            "Contexto de conversa",
            "Evolution API Integration"
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
    logger.info(f"🔗 Evolution API: {EVOLUTION_API_URL}")
    logger.info(f"📱 Instance: {EVOLUTION_INSTANCE}")
    logger.info(f"🧠 Groq Client: {'✅ Ready' if groq_client else '❌ Error'}")
    
    port = int(os.getenv('PORT', 5000))
    logger.info(f"🚀 Server starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
