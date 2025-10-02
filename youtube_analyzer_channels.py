import streamlit as st
import pandas as pd
import requests

# ----------------------------
# Função para obter o channelId
# ----------------------------
def get_channel_id(api_key, channel_input):
    base_url = "https://www.googleapis.com/youtube/v3/"
    
    if channel_input.startswith("@"):
        search_url = f"{base_url}search?part=snippet&type=channel&q={channel_input}&key={api_key}"
        resp = requests.get(search_url).json()
        if "items" in resp and resp["items"]:
            return resp["items"][0]["snippet"]["channelId"]
    elif "youtube.com" in channel_input:
        if "channel/" in channel_input:
            return channel_input.split("channel/")[-1].split("/")[0]
        elif "@" in channel_input:
            username = channel_input.split("@")[-1].split("/")[0]
            return get_channel_id(api_key, f"@{username}")
    else:
        return channel_input
    return None

# ----------------------------
# Função para coletar vídeos
# ----------------------------
def get_videos(api_key, channel_id, search_type="all", max_results=None):
    videos = []
    base_url = "https://www.googleapis.com/youtube/v3/"
    
    # playlist de uploads
    url = f"{base_url}channels?part=contentDetails&id={channel_id}&key={api_key}"
    resp = requests.get(url).json()
    if "items" not in resp or not resp["items"]:
        return []
    
    uploads_playlist_id = resp["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    
    next_page_token = None
    total_collected = 0
    
    while True:
        pl_url = f"{base_url}playlistItems?part=snippet&playlistId={uploads_playlist_id}&maxResults=50&key={api_key}"
        if next_page_token:
            pl_url += f"&pageToken={next_page_token}"
        
        pl_resp = requests.get(pl_url).json()
        if "items" not in pl_resp:
            break
        
        for item in pl_resp["items"]:
            video_id = item["snippet"]["resourceId"]["videoId"]
            title = item["snippet"]["title"]
            published = item["snippet"]["publishedAt"]
            
            stats_url = f"{base_url}videos?part=statistics,contentDetails&id={video_id}&key={api_key}"
            stats_resp = requests.get(stats_url).json()
            
            if "items" in stats_resp and stats_resp["items"]:
                stats = stats_resp["items"][0]
                statistics = stats["statistics"]
                content_details = stats["contentDetails"]
                
                views = int(statistics.get("viewCount", 0))
                likes = int(statistics.get("likeCount", 0))
                comments = int(statistics.get("commentCount", 0))
                duration = content_details["duration"]
                
                # cálculo do tempo em minutos (para separar shorts/longos)
                minutes = 0
                if "M" in duration:
                    try:
                        minutes = int(duration.split("M")[0].replace("PT", ""))
                    except:
                        minutes = 0
                
                # filtro de tipo
                if search_type == "shorts" and minutes >= 1:
                    continue
                if search_type == "longos" and minutes < 1:
                    continue
                
                # fórmula de viralidade
                viralidade = views + (likes * 5) + (comments * 10)
                
                videos.append({
                    "Título": title,
                    "Publicado em": published,
                    "Views": views,
                    "Likes": likes,
                    "Comentários": comments,
                    "Viralidade": viralidade,
                    "Link": f"https://youtu.be/{video_id}"
                })
                
                total_collected += 1
            
            if max_results and total_collected >= max_results:
                return videos
        
        next_page_token = pl_resp.get("nextPageToken")
        if not next_page_token:
            break
    
    return videos

# ----------------------------
# Interface Streamlit
# ----------------------------
st.set_page_config(page_title="YouTube Viral Monitor", layout="wide")
st.title("📊 YouTube Viral Videos Monitor")

api_key = st.text_input("🔑 Insira sua YouTube API Key:")
channel_input = st.text_input("📺 Insira o canal (ex: @canal, URL ou Channel ID):")

search_type = st.radio("Tipo de pesquisa:", ["Todos os vídeos", "Apenas Shorts", "Apenas Longos"])
max_videos_option = st.radio("Quantos vídeos deseja analisar?", ["Canal inteiro", "Definir quantidade"])

max_results = None
if max_videos_option == "Definir quantidade":
    max_results = st.number_input("Digite o número de vídeos (ex: 200)", min_value=10, max_value=5000, value=200, step=10)

if st.button("🔍 Analisar Canal"):
    if not api_key or not channel_input:
        st.error("Por favor, insira a API Key e o canal.")
    else:
        channel_id = get_channel_id(api_key, channel_input)
        if not channel_id:
            st.error("❌ Canal não encontrado ou inválido.")
        else:
            st.info("⏳ Coletando vídeos, aguarde...")
            
            type_map = {
                "Todos os vídeos": "all",
                "Apenas Shorts": "shorts",
                "Apenas Longos": "longos"
            }
            
            videos = get_videos(api_key, channel_id, type_map[search_type], max_results)
            
            if not videos:
                st.error("Nenhum vídeo encontrado para este canal.")
            else:
                df = pd.DataFrame(videos)
                df = df.sort_values(by="Viralidade", ascending=False).reset_index(drop=True)
                
                st.success(f"✅ {len(df)} vídeos analisados com sucesso!")
                
                st.subheader("🏆 Top 5 vídeos mais virais (ranking pela fórmula):")
                st.dataframe(df.head(5), use_container_width=True)
                
                csv = df.to_csv(index=False, sep=";").encode("utf-8")
                st.download_button(
                    label="📥 Baixar CSV completo",
                    data=csv,
                    file_name="youtube_videos.csv",
                    mime="text/csv"
                )
