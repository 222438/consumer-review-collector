const prompt = document.querySelector('#prompt');
const status = document.querySelector('#buildStatus');
document.querySelectorAll('.chip').forEach(chip => chip.addEventListener('click', () => {
  prompt.value = `Build a polished ${chip.textContent.toLowerCase()} for a modern startup`;
  prompt.focus();
}));
document.querySelector('#buildBtn').addEventListener('click', () => {
  const value = prompt.value.trim();
  status.hidden = false;
  status.textContent = value ? `正在为“${value}”准备初始版本…` : '请先描述你想构建的产品。';
  if (value) setTimeout(() => { status.textContent = '初始版本已准备好。继续补充细节即可迭代。'; }, 900);
});
document.querySelector('#newProject').addEventListener('click', () => { prompt.value = ''; prompt.focus(); status.hidden = true; });
