'use strict';
const image=document.getElementById('image'),stage=document.getElementById('stage'),status=document.getElementById('status');
function setOriginal(value){stage.classList.toggle('original',value);document.getElementById('fit').setAttribute('aria-pressed',String(!value));document.getElementById('original').setAttribute('aria-pressed',String(value));stage.scrollTo(0,0)}
document.getElementById('fit').onclick=()=>setOriginal(false);
document.getElementById('original').onclick=()=>setOriginal(true);
image.onclick=()=>setOriginal(!stage.classList.contains('original'));
image.onload=()=>{status.textContent=`${image.naturalWidth.toLocaleString()} × ${image.naturalHeight.toLocaleString()} px`};
image.onerror=()=>{status.textContent='画像を読み込めません。SSD の接続を確認してください。'};
image.src='/api/image/'+encodeURIComponent(location.pathname.split('/').pop())+'?original=1';
