'use client';

import { useEffect, useState } from 'react';
import { useUser } from '@stackframe/stack';
import { HelpCircle } from 'lucide-react';
import { Layout } from '@/components/Layout';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { useConfirmDialog } from '@/contexts/NotificationContext';

interface Proxy {
  id: string;
  name: string;
  proxy_type: string;
  proxy_host: string;
  proxy_port: number;
  proxy_country?: string;
  validation_status?: string;
  last_validation_at?: string | null;
  validation_latency_ms?: number | null;
  created_at: string;
  updated_at: string;
}

const PROXY_TYPES = [
  { value: 'SOCKS5', label: 'SOCKS5' },
  { value: 'HTTP', label: 'HTTP' },
  { value: 'MTProto', label: 'MTProto' },
];

export default function ProxiesPage() {
  const user = useUser();
  const { isConnected } = useBackendConnection();
  const { confirmDialog } = useConfirmDialog();
  const [proxies, setProxies] = useState<Proxy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    proxy_type: 'SOCKS5',
    proxy_host: '',
    proxy_port: 1080,
    proxy_username: '',
    proxy_password: '',
    proxy_country: '',
  });

  const loadProxies = async () => {
    if (!user) return;
    const api = initApiClient(createTokenGetter(user));
    try {
      const data = await api.get<Proxy[]>('/proxies');
      setProxies(data ?? []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar proxies');
      setProxies([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!user) return;
    setLoading(true);
    loadProxies();
  }, [user]);

  const handleSubmit = async () => {
    if (!user) return;
    if (!formData.name.trim()) {
      setFormError('El nombre es obligatorio');
      return;
    }
    if (!formData.proxy_host.trim()) {
      setFormError('El host es obligatorio');
      return;
    }
    if (!formData.proxy_port || formData.proxy_port < 1 || formData.proxy_port > 65535) {
      setFormError('Puerto inválido (1-65535)');
      return;
    }
    setFormError(null);
    setIsSubmitting(true);
    const api = initApiClient(createTokenGetter(user));
    try {
      const payload: Record<string, unknown> = {
        name: formData.name.trim(),
        proxy_type: formData.proxy_type,
        proxy_host: formData.proxy_host.trim(),
        proxy_port: formData.proxy_port,
      };
      if (formData.proxy_username) payload.proxy_username = formData.proxy_username;
      if (formData.proxy_password) payload.proxy_password = formData.proxy_password;
      if (formData.proxy_country) payload.proxy_country = formData.proxy_country;
      if (editingId) {
        await api.put(`/proxies/${editingId}`, payload);
      } else {
        await api.post('/proxies', payload);
      }
      setFormData({ name: '', proxy_type: 'SOCKS5', proxy_host: '', proxy_port: 1080, proxy_username: '', proxy_password: '', proxy_country: '' });
      setShowAddForm(false);
      setEditingId(null);
      setError(null);
      await loadProxies();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Error al guardar proxy');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEdit = (p: Proxy) => {
    setEditingId(p.id);
    setFormData({
      name: p.name,
      proxy_type: p.proxy_type,
      proxy_host: p.proxy_host,
      proxy_port: p.proxy_port,
      proxy_username: '',
      proxy_password: '',
      proxy_country: p.proxy_country ?? '',
    });
    setShowAddForm(true);
    setFormError(null);
  };

  const handleCancelForm = () => {
    setShowAddForm(false);
    setEditingId(null);
    setFormData({ name: '', proxy_type: 'SOCKS5', proxy_host: '', proxy_port: 1080, proxy_username: '', proxy_password: '', proxy_country: '' });
    setFormError(null);
  };

  const handleDelete = async (proxyId: string) => {
    if (!user) return;
    const ok = await confirmDialog({
      title: 'Eliminar proxy',
      description: '¿Eliminar este proxy? No podrás recuperarlo. No se puede eliminar si está en uso por estrategias activas.',
      confirmLabel: 'Eliminar',
      cancelLabel: 'Cancelar',
      variant: 'danger',
    });
    if (!ok) return;
    const api = initApiClient(createTokenGetter(user));
    try {
      await api.delete(`/proxies/${proxyId}`);
      await loadProxies();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al eliminar proxy');
    }
  };

  const handleValidate = async (proxyId: string) => {
    if (!user) return;
    const api = initApiClient(createTokenGetter(user));
    try {
      await api.post(`/proxies/${proxyId}/validate`);
      await loadProxies();
    } catch {
      await loadProxies();
    }
  };

  const statusLabel = (s?: string | null) => {
    if (!s) return '—';
    if (s === 'healthy') return <span className="text-green-600 dark:text-green-400">healthy</span>;
    if (s === 'unhealthy') return <span className="text-red-600 dark:text-red-400">unhealthy</span>;
    return <span className="text-muted-foreground">unknown</span>;
  };

  if (loading) {
    return (
      <Layout>
        <LoadingSpinner text="Cargando proxies..." />
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold text-gradient">Gestión de Proxies</h1>
          <button
            type="button"
            onClick={() => {
              if (showAddForm) {
                handleCancelForm();
              } else {
                setShowAddForm(true);
                setEditingId(null);
              }
            }}
            disabled={!isConnected}
            title={!isConnected ? 'Conecta el backend para agregar proxies' : undefined}
            className="px-4 py-2 rounded-xl font-semibold text-white transition-all duration-200 gradient-premium hover:opacity-90 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 cursor-pointer"
          >
            {showAddForm ? 'Cancelar' : '+ Agregar Proxy'}
          </button>
        </div>

        {error && (
          <div className="rounded-lg p-4 bg-destructive/10 border border-destructive/30 text-destructive text-sm">
            {error}
          </div>
        )}

        {showAddForm && (
          <div className="glass rounded-2xl shadow-premium p-6">
            <h2 className="text-xl font-semibold mb-4">{editingId ? 'Editar proxy' : 'Agregar proxy'}</h2>
            {formError && (
              <div className="mb-4 p-3 rounded-lg bg-destructive/10 border border-destructive/30 text-destructive text-sm">
                {formError}
              </div>
            )}
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Nombre <span className="text-destructive">*</span></label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => { setFormData({ ...formData, name: e.target.value }); setFormError(null); }}
                  className="w-full px-3 py-2 border border-input rounded-md bg-background"
                  placeholder="Ej: Mobile ES, Proxy EU..."
                />
              </div>
              <div>
                <label className="flex items-center gap-1.5 text-sm font-medium mb-2">
                  Tipo
                  <Dialog>
                    <DialogTrigger asChild>
                      <button type="button" className="inline-flex text-muted-foreground hover:text-foreground transition-colors cursor-help" aria-label="Ayuda sobre tipos de proxy">
                        <HelpCircle className="h-3.5 w-3.5" />
                      </button>
                    </DialogTrigger>
                    <DialogContent className="max-w-md">
                      <DialogHeader>
                        <DialogTitle>Tipos de proxy</DialogTitle>
                      </DialogHeader>
                      <div className="text-sm text-muted-foreground space-y-3">
                        <p><strong>SOCKS5</strong> — El más común en proxies residenciales o móviles. Prueba este primero si no sabes el tipo.</p>
                        <p><strong>HTTP</strong> — Para tráfico web (HTTP/HTTPS). Usado típicamente en scraping o proxies web.</p>
                        <p><strong>MTProto</strong> — Solo para Telegram. Si tu proveedor es específico de Telegram, suele ser este.</p>
                        <p className="text-foreground font-medium">Si la validación falla, prueba otro tipo (credenciales o tipo incorrecto).</p>
                        <p className="text-xs">La latencia se mide al validar: una conexión real comprueba que el proxy funciona.</p>
                      </div>
                    </DialogContent>
                  </Dialog>
                </label>
                <Select value={formData.proxy_type} onValueChange={(v) => setFormData({ ...formData, proxy_type: v })}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Seleccionar tipo" />
                  </SelectTrigger>
                  <SelectContent>
                    {PROXY_TYPES.map((t) => (
                      <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Host <span className="text-destructive">*</span></label>
                  <input
                    type="text"
                    value={formData.proxy_host}
                    onChange={(e) => { setFormData({ ...formData, proxy_host: e.target.value }); setFormError(null); }}
                    className="w-full px-3 py-2 border border-input rounded-md bg-background"
                    placeholder="IP o hostname"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Puerto <span className="text-destructive">*</span></label>
                  <input
                    type="number"
                    value={formData.proxy_port}
                    onChange={(e) => { setFormData({ ...formData, proxy_port: parseInt(e.target.value, 10) || 1080 }); setFormError(null); }}
                    min={1}
                    max={65535}
                    className="w-full px-3 py-2 border border-input rounded-md bg-background"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Usuario (opcional)</label>
                <input
                  type="text"
                  value={formData.proxy_username}
                  onChange={(e) => setFormData({ ...formData, proxy_username: e.target.value })}
                  className="w-full px-3 py-2 border border-input rounded-md bg-background"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">{editingId ? 'Nueva contraseña (dejar vacío para no cambiar)' : 'Contraseña (opcional)'}</label>
                <input
                  type="password"
                  value={formData.proxy_password}
                  onChange={(e) => setFormData({ ...formData, proxy_password: e.target.value })}
                  className="w-full px-3 py-2 border border-input rounded-md bg-background"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">País (opcional)</label>
                <input
                  type="text"
                  value={formData.proxy_country}
                  onChange={(e) => setFormData({ ...formData, proxy_country: e.target.value })}
                  className="w-full px-3 py-2 border border-input rounded-md bg-background"
                  placeholder="ES, US..."
                />
              </div>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 font-medium disabled:opacity-60 transition-all duration-200 hover:scale-105 disabled:hover:scale-100 cursor-pointer"
                >
                  {isSubmitting ? 'Guardando…' : (editingId ? 'Guardar cambios' : 'Agregar proxy')}
                </button>
                <button
                  type="button"
                  onClick={handleCancelForm}
                  className="px-4 py-2 border border-border rounded-md hover:bg-muted transition-all duration-200 hover:scale-105 cursor-pointer"
                >
                  Cancelar
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="glass rounded-2xl shadow-premium overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Nombre</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Tipo</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Host:Puerto</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">País</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Estado</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Latencia</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {proxies.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-8 text-center text-muted-foreground">
                    No hay proxies. Agrega uno para usarlo en estrategias.
                  </td>
                </tr>
              ) : (
                proxies.map((p) => (
                  <tr key={p.id} className="hover:bg-muted/30 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-foreground">{p.name}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">{p.proxy_type}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-muted-foreground">{p.proxy_host}:{p.proxy_port}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">{p.proxy_country || '—'}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">{statusLabel(p.validation_status)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                      {p.validation_latency_ms != null ? `${p.validation_latency_ms}ms` : '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className="flex items-center gap-3">
                        <button type="button" onClick={() => handleValidate(p.id)} className="inline-block text-primary hover:underline font-medium transition-all duration-200 hover:scale-105 cursor-pointer">Validar</button>
                        <button type="button" onClick={() => handleEdit(p)} className="inline-block text-primary hover:underline font-medium transition-all duration-200 hover:scale-105 cursor-pointer">Editar</button>
                        <button type="button" onClick={() => handleDelete(p.id)} className="inline-block text-destructive hover:underline font-medium transition-all duration-200 hover:scale-105 cursor-pointer">Eliminar</button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="mt-6 p-4 rounded-lg bg-muted/50 border border-border text-sm text-muted-foreground">
          ¿Necesitas proxies? Puedes comprarlos aquí:{' '}
          <a
            href="https://www.webshare.io/?referral_code=4a6vwvuzv2fv"
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary hover:underline font-medium underline decoration-primary/60 cursor-pointer hover:decoration-primary transition-colors"
          >
            webshare.io →
          </a>
          <span className="ml-1">(SOCKS5, HTTP, residenciales, datacenter)</span>
        </div>
      </div>
    </Layout>
  );
}
