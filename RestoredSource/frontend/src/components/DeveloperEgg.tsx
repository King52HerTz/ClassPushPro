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
    const width = 520, height = 220, ratio = Math.min(window.devicePixelRatio || 1, 2);
    element.width = width * ratio; element.height = height * ratio;
    context.scale(ratio, ratio);
    const colors = ['#1677ff', '#9a7ce8', '#f2b84b', '#ed85a6', '#48b9a1'];
    const sparks = [0, 1, 2].flatMap(burst => Array.from({ length: 52 }, (_, i) => ({
      x: [115, 390, 260][burst], y: [90, 80, 55][burst], delay: burst * 450,
      angle: i / 52 * Math.PI * 2, speed: 30 + Math.random() * 85, color: colors[i % colors.length],
    })));
    const start = performance.now();
    let frame = 0;
    const draw = (now: number) => {
      context.clearRect(0, 0, width, height);
      for (const spark of sparks) {
        const age = (now - start - spark.delay) / 1000;
        if (age < 0 || age > 1.6) continue;
        context.globalAlpha = Math.max(0, 1 - age / 1.6);
        context.fillStyle = spark.color;
        context.beginPath();
        context.arc(spark.x + Math.cos(spark.angle) * spark.speed * age,
          spark.y + Math.sin(spark.angle) * spark.speed * age + 35 * age * age, 2, 0, Math.PI * 2);
        context.fill();
      }
      if (now - start < 2700) frame = requestAnimationFrame(draw);
      else context.clearRect(0, 0, width, height);
    };
    frame = requestAnimationFrame(draw);
    return () => { cancelAnimationFrame(frame); context.clearRect(0, 0, width, height); };
  }, [open]);

  return <Modal open={open} onCancel={onClose} forceRender title="开发者的秘密基地" footer={null} width={560}>
    <div className="developer-egg">
      <canvas ref={canvas} className="egg-fireworks" aria-hidden="true" />
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
