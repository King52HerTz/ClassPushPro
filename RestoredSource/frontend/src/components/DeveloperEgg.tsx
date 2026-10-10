import { useEffect, useRef } from 'react';
import { Button, Modal } from 'antd';
import { GithubOutlined, GlobalOutlined } from '@ant-design/icons';
import { GITHUB_REPO_URL } from '../constants';

export default function DeveloperEgg({ open, onClose }: { open: boolean; onClose: () => void }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    if (!open || !canvas.current || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const element = canvas.current;
    const context = element.getContext('2d');
    if (!context) return;
    // Ant Design may begin opening while the force-rendered dialog is still hidden.
    const width = element.clientWidth || Math.max(1, Math.min(480, window.innerWidth - 80));
    const height = 180, ratio = Math.min(window.devicePixelRatio || 1, 2);
    element.width = width * ratio; element.height = height * ratio;
    context.scale(ratio, ratio);
    const colors = ['#8dcaff', '#ffd58a', '#d4b2ff'];
    const bursts = [0, 1, 2].map(index => ({
      x: width * [.24, .76, .5][index], y: [65, 60, 40][index], delay: index * 380,
      color: colors[index],
      sparks: Array.from({ length: 48 }, (_, i) => ({
        angle: i / 48 * Math.PI * 2, speed: 45 + Math.random() * 80,
        size: .8 + Math.random() * .9,
      })),
    }));
    const start = performance.now();
    let frame = 0;
    const draw = (now: number) => {
      context.clearRect(0, 0, width, height);
      context.globalCompositeOperation = 'lighter';
      for (const burst of bursts) {
        const elapsed = (now - start - burst.delay) / 1000;
        if (elapsed < 0 || elapsed > 1.8) continue;
        context.fillStyle = context.strokeStyle = context.shadowColor = burst.color;
        context.shadowBlur = 6;
        context.lineWidth = 1.2;
        if (elapsed < .4) {
          const progress = 1 - Math.pow(1 - elapsed / .4, 2);
          const y = height - 16 - (height - 16 - burst.y) * progress;
          const trail = context.createLinearGradient(0, y, 0, y + 24);
          trail.addColorStop(0, burst.color); trail.addColorStop(1, 'transparent');
          context.globalAlpha = 1;
          context.strokeStyle = trail;
          context.beginPath(); context.moveTo(burst.x, y); context.lineTo(burst.x, y + 24); context.stroke();
          continue;
        }
        const age = elapsed - .4;
        const travel = (1 - Math.exp(-2.4 * age)) / 2.4;
        const tailTravel = (1 - Math.exp(-2.4 * Math.max(0, age - .08))) / 2.4;
        for (const spark of burst.sparks) {
          const vx = Math.cos(spark.angle) * spark.speed, vy = Math.sin(spark.angle) * spark.speed;
          const x = burst.x + vx * travel, y = burst.y + vy * travel + 22 * age * age;
          context.globalAlpha = Math.pow(1 - age / 1.4, 1.5);
          context.beginPath();
          context.moveTo(burst.x + vx * tailTravel, burst.y + vy * tailTravel + 22 * Math.max(0, age - .08) ** 2);
          context.lineTo(x, y); context.stroke();
          context.beginPath(); context.arc(x, y, spark.size, 0, Math.PI * 2); context.fill();
        }
      }
      if (now - start < 2700) frame = requestAnimationFrame(draw);
      else context.clearRect(0, 0, width, height);
    };
    frame = requestAnimationFrame(draw);
    return () => { cancelAnimationFrame(frame); context.clearRect(0, 0, width, height); };
  }, [open]);

  return <Modal open={open} onCancel={onClose} forceRender centered title="开发者的秘密基地" footer={null} width={560} styles={{ body: { maxHeight: 'calc(100dvh - 160px)', overflowY: 'auto' } }}>
    <div className="developer-egg">
      <div className="egg-sky" aria-hidden="true">
        <canvas ref={canvas} className="egg-fireworks" />
        <span className="egg-sky-caption">每一颗 Star，都值得一场小烟花</span>
      </div>
      <span className="egg-kicker">HIDDEN SIDE QUEST · 隐藏支线已解锁</span>
      <h2>恭喜！你抓到了<br />一只野生开发者。</h2>
      <p>白天和课表斗智斗勇，晚上和 Bug 极限拉扯。<br />这个小项目的精神食粮，是你顺手点亮的一颗 Star。</p>
      <div className="egg-note">不求投喂，只求星星。<br />给代码一点排面，让开发者少掉两根头发。<small>友情提示：Star 不加学分，但真的会让作者开心。</small></div>
      <div className="egg-actions">
        <Button type="primary" icon={<GithubOutlined />} onClick={() => window.open(GITHUB_REPO_URL, '_blank', 'noopener,noreferrer')}>去 GitHub 点亮 Star</Button>
        <Button icon={<GlobalOutlined />} onClick={() => window.open('https://eliauk312.top/', '_blank', 'noopener,noreferrer')}>去博客串个门</Button>
      </div>
      <p className="egg-address">开发者博客 · eliauk312.top</p>
      <Button type="text" onClick={onClose}>先去学习，下次一定（真的）</Button>
    </div>
  </Modal>;
}
