import { Channel } from '@/lib/leadgen-api'

const CHANNEL_CONFIG: Record<Channel, { label: string; color: string }> = {
  web: { label: 'Web', color: '#3B82F6' },
  telegram: { label: 'TG', color: '#0088CC' },
  whatsapp: { label: 'WA', color: '#25D366' },
  vk: { label: 'VK', color: '#0077FF' },
  email: { label: 'Email', color: '#6B7280' },
  ok: { label: 'OK', color: '#FF7700' },
  facebook: { label: 'FB', color: '#1877F2' },
  avito: { label: 'Авито', color: '#00AAFF' },
  callback: { label: 'Звонок', color: '#8B5CF6' },
  max: { label: 'Макс', color: '#FF4444' },
}

export default function ChannelBadge({ channel }: { channel: Channel }) {
  const cfg = CHANNEL_CONFIG[channel] || { label: channel, color: '#6B7280' }
  return (
    <span
      className="text-xs font-medium px-2 py-0.5 rounded-full text-white"
      style={{ backgroundColor: cfg.color }}
    >
      {cfg.label}
    </span>
  )
}
