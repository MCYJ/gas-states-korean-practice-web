'use strict';
const worksheet = document.getElementById('worksheet');
if (worksheet) {
  const pressure = document.getElementById('pressure');
  const temperature = document.getElementById('temperature');
  const korean = document.documentElement.lang === 'ko';
  const update = () => {
    const p = Number(pressure.value);
    const t = Number(temperature.value);
    const ratio = (200 / p) * (t / 300);
    document.getElementById('pressure-label').value = `${p} kPa`;
    document.getElementById('temperature-label').value = `${t} K`;
    document.getElementById('volume').value = `${(10 * ratio).toFixed(2)} L`;
    document.getElementById('ratio').textContent = korean
      ? `초기 부피의 ${ratio.toFixed(2)}배`
      : `${ratio.toFixed(2)} times the initial volume`;
  };
  worksheet.addEventListener('input', update);
  worksheet.addEventListener('submit', event => event.preventDefault());
  update();
}
