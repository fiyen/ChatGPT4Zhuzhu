import streamlit as st
import openai
import traceback
import json
from IPython.display import HTML

# 设置文本框和状态变量
my_api_key = "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"    # 在这里输入你的 API 密钥
initial_prompt = "请输入起始提示..."
chatbot = []
context = []
systemPrompt = st.session_state.get("systemPrompt", initial_prompt)
myKey = my_api_key
topic = "未命名对话历史记录"


def parse_text(text):
  lines = text.split("\n")
  for i, line in enumerate(lines):
    if "```" in line:
      items = line.split('`')
      if items[-1]:
        lines[i] = f'<pre><code class="{items[-1]}">'
      else:
        lines[i] = f'</code></pre>'
    else:
      if i > 0:
        line = line.replace("<", "&lt;")
        line = line.replace(">", "&gt;")
        lines[i] = '<br/>' + line.replace(" ", "&nbsp;")
  return "".join(lines)


def get_response(system, context, myKey, raw=False):
  openai.api_key = myKey
  response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[system, *context],
  )
  openai.api_key = ""
  if raw:
    return response
  else:
    statistics = f'本次对话Tokens用量【{response["usage"]["total_tokens"]} / 4096】 （ 提问+上文 {response["usage"]["prompt_tokens"]}，回答 {response["usage"]["completion_tokens"]} ）'
    message = response["choices"][0]["message"]["content"]

    message_with_stats = f'{message}\n\n================\n\n{statistics}'
    # message_with_stats = markdown.markdown(message_with_stats)

    return message, parse_text(message_with_stats)


def predict(chatbot, input_sentence, system, context, myKey):
  if len(input_sentence) == 0:
    return []
  context.append({"role": "user", "content": f"{input_sentence}"})

  try:
    message, message_with_stats = get_response(system, context, myKey)
  except:
    chatbot.append((input_sentence, "请求失败，请检查API-key是否正确。"))
    return chatbot, context

  print(message)
  context.append({"role": "assistant", "content": message})

  chatbot.append((input_sentence, message_with_stats))

  return chatbot, context


def retry(chatbot, system, context, myKey):
  if len(context) == 0:
    return [], []
  try:
    message, message_with_stats = get_response(system, context[:-1], myKey)
  except:
    chatbot.append(("重试请求", "请求失败，请检查API-key是否正确。"))
    return chatbot, context
  context[-1] = {"role": "assistant", "content": message}

  chatbot[-1] = (context[-2]["content"], message_with_stats)
  return chatbot, context


def delete_last_conversation(chatbot, context):
  if len(context) == 0:
    return [], []
  chatbot = chatbot[:-1]
  context = context[:-2]
  return chatbot, context


def reduce_token(chatbot, system, context, myKey):
  context.append({"role": "user", "content": "请帮我总结一下上述对话的内容，实现减少tokens的同时，保证对话的质量。在总结中不要加入这一句话。"})

  response = get_response(system, context, myKey, raw=True)

  statistics = f'本次对话Tokens用量【{response["usage"]["completion_tokens"] + 12 + 12 + 8} / 4096】'
  optmz_str = parse_text(
    f'好的，我们之前聊了:{response["choices"][0]["message"]["content"]}\n\n================\n\n{statistics}')
  chatbot.append(("请帮我总结一下上述对话的内容，实现减少tokens的同时，保证对话的质量。", optmz_str))

  context = []
  context.append({"role": "user", "content": "我们之前聊了什么?"})
  context.append({"role": "assistant", "content": f'我们之前聊了：{response["choices"][0]["message"]["content"]}'})
  return chatbot, context


def save_chat_history(filepath, system, context):
  if filepath == "":
    return
  history = {"system": system, "context": context}
  with open(f"{filepath}.json", "w") as f:
    json.dump(history, f)


def load_chat_history(fileobj):
  with open(fileobj.name, "r") as f:
    history = json.load(f)
  context = history["context"]
  chathistory = []
  for i in range(0, len(context), 2):
    chathistory.append((parse_text(context[i]["content"]), parse_text(context[i + 1]["content"])))
  return chathistory, history["system"], context, history["system"]["content"]


def get_history_names():
  with open("history.json", "r") as f:
    history = json.load(f)
  return list(history.keys())


def reset_state():
  return [], []


def update_system(new_system_prompt):
  return {"role": "system", "content": new_system_prompt}


def set_apikey(new_api_key, myKey):
  old_api_key = myKey
  try:
    get_response(update_system(initial_prompt), [{"role": "user", "content": "test"}], new_api_key)
  except:
    traceback.print_exc()
    print("API key校验失败，请检查API key是否正确，或者检查网络是否畅通。")
    return "无效的api-key", myKey
  encryption_str = "验证成功，api-key已做遮挡处理：" + new_api_key[:4] + "..." + new_api_key[-4:]
  return encryption_str, new_api_key


# 布局
st.title("对话窗口")
col1, col2 = st.columns([12, 1])
with col1:
  txt = st.text_area("输入你的文本：", value="", key="textInput", max_chars=4096,
                                          placeholder="点击输入", label_visibility="hidden")
with col2:
  st.text("")
  st.text("")
  st.text("")
  st.text("")
  submitBtn = col2.button("🚀")

col3, col4, col5, col6 = st.columns(4)
emptyBtn = col3.button("🧹 新的对话")
retryBtn =col4.button("🔄 重新生成")
delLastBtn = col5.button("🗑️ 删除上条对话")
reduceTokenBtn = col6.button("♻️ 优化Tokens")

with st.sidebar.expander("API Key"):
  keyTxt = st.text_input("", my_api_key)

with st.sidebar.expander("设置System Prompt"):
  newSystemPrompt = st.text_input("更改 System prompt", initial_prompt)
  systemPromptDisplay = st.text_input("目前的 System prompt", value=systemPrompt)

with st.sidebar.expander("保存/读取"):
  st.write("保存/加载对话历史记录(在文本框中输入文件名，点击“保存对话”按钮，历史记录文件会被存储到本地)")
  saveFileName = st.text_input("保存对话", "对话历史记录")
  saveBtn = st.button("💾 保存对话")
  uploadBtn = st.file_uploader("📂 读取对话", type=["json"])

# 绑定组件事件函数
if submitBtn:
    predict(chatbot, txt, systemPrompt, context, myKey)
    txt = ""

if emptyBtn:
    chatbot, context = reset_state()

if retryBtn:
    retry(chatbot, systemPrompt, context, myKey)

if delLastBtn:
    delete_last_conversation(chatbot, context)

if reduceTokenBtn:
    reduce_token(chatbot, systemPrompt, context, myKey)

if keyTxt != my_api_key:
    set_apikey(keyTxt, myKey)

if newSystemPrompt != systemPrompt:
    systemPrompt = update_system(newSystemPrompt)
    st.session_state["systemPrompt"] = systemPrompt
    systemPromptDisplay = systemPrompt

if saveBtn:
    save_chat_history(saveFileName, systemPrompt, context)

if uploadBtn is not None:
    load_chat_history(uploadBtn)

# 显示聊天记录

#
# st.markdown("""
#     <div style="border: 2px solid #eee; background-color: #eef;
#                 border-radius: 5px; padding: 10px; box-sizing: border-box;
#                 display: flex; justify-content: space-between; align-items: center;"">
#         <p style="margin: 0;"><h4 style="text-align: center">聊天记录</h4>
#         <br>这是聊天记录</p>
#         <a href="#" onclick="copyToClipboard(this.parentNode.parentNode.querySelector('p'))">📋</a>
#
#     </div>
#     <script>
#         function copyToClipboard(node) {
#             const text = node.innerText;
#             navigator.clipboard.writeText(text)
#                 .then(() => console.log('已复制到剪贴板'))
#                 .catch(() => console.log('复制失败'));
#         }
#     </script>
# """, unsafe_allow_html=True)
#
# st.markdown("""
#     <div style="border: 2px solid #555; background-color: #eee;
#                 border-radius: 5px; padding: 10px; box-sizing: border-box;
#                 display: flex; justify-content: space-between; align-items: center;">
#         <p style="margin: 0;">这是一个框框起来的内容</p>
#         <a href="#" onclick="copyToClipboard(this.parentNode.parentNode.querySelector('p'))">📋</a>
#     </div>
#     <script>
#         function copyToClipboard(node) {
#             const text = node.innerText;
#             navigator.clipboard.writeText(text)
#                 .then(() => console.log('已复制到剪贴板'))
#                 .catch(() => console.log('复制失败'));
#         }
#     </script>
# """, unsafe_allow_html=True)

def show_dialog(text):
#   style = """<style>
#   .dialog {
#     display: flex;
#     flex-direction: column;
#   }
#
#   .bubble {
#     width: 80%;
#     padding: 10px;
#     margin: 5px;
#     border-radius: 10px;
#   }
#
#   .left-bubble {
#     background-color: #EEEEEE;
#   }
#
#   .right-bubble {
#     background-color: #87CEFA;
#     align-self: flex-end;
#   }
#
#   .avatar-left {
#   width: 50px;
#   height: 50px;
#   border-radius: 50%;
#   float: left; /* 左浮动 */
#   margin-right: 10px; /* 头像与对话气泡之间的间隔 */
# }
#
# .avatar-right {
#   width: 50px;
#   height: 50px;
#   border-radius: 50%;
#   float: right; /* 右浮动 */
#   margin-left: 10px; /* 头像与对话气泡之间的间隔 */
# }
# </style>"""
  style = """
  <style>
        body {
            background-color: #f7f7f7;
            margin: 0;
            padding: 0;
            font-family: Arial, Helvetica, sans-serif;
            font-size: 14px;
            line-height: 1.5;
        }

        .chat-wrapper {
            max-width: 500px;
            margin: 50px auto;
            background-color: #fff;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,.3);
        }

        .chat-header {
            background-color: #333;
            color: #fff;
            padding: 20px;
            border-radius: 5px 5px 0 0;
            font-size: 20px;
            text-transform: uppercase;
        }

        .chat-box {
            height: 400px;
            overflow-y: auto;
            padding: 10px;
        }

        .bubble {
            margin-bottom: 20px;
            display: flex;
            align-items: flex-start;
        }

        .user-avatar {
            width: 50px;
            height: 50px;
            margin-right: 10px;
            border-radius: 50%;
        }

        .bot-avatar {
            width: 50px;
            height: 50px;
            margin-left: 10px;
            border-radius: 50%;
        }

        .user-bubble {
            background-color: #92DCE5;
            color: white;
            padding: 10px;
            border-radius: 10px;
            max-width: 70%;
        }

        .bot-bubble {
            background-color: #E5DADA;
            padding: 10px;
            border-radius: 10px;
            max-width: 70%;
        }

        .input-wrapper {
            display: flex;
            align-items: center;
            padding: 20px;
            border-top: 1px solid #f2f2f2;
        }

        #message-input {
            flex: 1;
            padding: 10px;
            margin-right: 10px;
            border: none;
            border-radius: 5px;
            background-color: #f2f2f2;
            font-size: 14px;
        }

        #send-btn {
            border: none;
            border-radius: 10px;
            background-color: #333;
            color: #fff;
            padding: 10px 20px;
            font-size: 14px;
            cursor: pointer;
        }
    </style>
  """
  html = """
  <div class="chat-wrapper">
      <div class="chat-header">聊天记录</div>
        <div class="chat-box">
          {}
        </div>
      </div>
  </div>
  """.format(text)
  st.write(style, unsafe_allow_html=True)
  st.write(HTML(html))

icon_left = '<img src="yangyang.ico" width="20px" height="20px"/>'
icon_right = '<img src="zhuzhu.ico" width="20px" height="20px"/>'

# 对话整合
def form_dialog(words, dialog=None, dir="left"):
  pass

show_dialog("""<div class="chat-box">
            <div class="bubble">
                <img src="yangyang.jpg" class="user-avatar">
                <div class="user-bubble">你好，机器人。我想咨询一下关于产品的信息。</div>
            </div>
            <div class="bubble">
                <img src="zhuzhu.jpg" class="bot-avatar">
                <div class="bot-bubble">你好，很高兴能为您服务。您需要了解那方面的信息呢？</div>
            </div>
        </div>""")

for message in context:
    if message["role"] == "user":
        st.write(f"{message['role']}: {message['content']}")
    else:
        st.write(f"{message['role']}: {message['content']}")
