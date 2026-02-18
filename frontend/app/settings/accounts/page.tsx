'use client';

import { useState, useEffect } from 'react';
import { useUser, useStackApp } from '@stackframe/stack';
import Link from 'next/link';
import { Layout } from '@/components/Layout';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { initApiClient, createTokenGetter, ApiResponseError } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog';
import { MessageSquare, Link2, ArrowRight, Plus, Loader2 } from 'lucide-react';
import { toast } from '@/components/ui/sonner';

interface ExternalSource {
  id: string;
  name: string;
  connector_type: string;
  is_active: boolean;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

interface TelegramDialogItem {
  id: string;
  title: string;
  is_channel: boolean;
}

const TELEGRAM_STEPS = ['phone', 'code', 'chats', 'save'] as const;
/** Telegram limita solicitudes de código. Mínimo 2 min entre peticiones para evitar bloqueo. */
const SEND_CODE_COOLDOWN_SECONDS = 120;

function fetchSources(
  user: NonNullable<ReturnType<typeof useUser>>,
  stackApp: NonNullable<ReturnType<typeof useStackApp>>,
  setSources: (s: ExternalSource[]) => void,
  setError: (e: string | null) => void,
  setLoading: (l: boolean) => void
) {
  const api = initApiClient(createTokenGetter(user, stackApp));
  api
    .get<ExternalSource[]>('/external-data-sources')
    .then((data) => setSources(Array.isArray(data) ? data : []))
    .catch(() => setError('Error al cargar cuentas'))
    .finally(() => setLoading(false));
}

export default function AccountsSettingsPage() {
  const user = useUser();
  const stackApp = useStackApp();
  const [loading, setLoading] = useState(true);
  const [sources, setSources] = useState<ExternalSource[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [ps3838Open, setPs3838Open] = useState(false);
  const [ps3838Name, setPs3838Name] = useState('');
  const [ps3838User, setPs3838User] = useState('');
  const [ps3838Password, setPs3838Password] = useState('');
  const [ps3838Submitting, setPs3838Submitting] = useState(false);
  const [ps3838FormError, setPs3838FormError] = useState<string | null>(null);

  const [telegramOpen, setTelegramOpen] = useState(false);
  const [telegramStep, setTelegramStep] = useState<(typeof TELEGRAM_STEPS)[number]>('phone');
  const [telegramPhone, setTelegramPhone] = useState('');
  const [telegramPhoneCodeHash, setTelegramPhoneCodeHash] = useState<string | null>(null);
  const [telegramSessionPendingHex, setTelegramSessionPendingHex] = useState<string | null>(null);
  const [telegramCode, setTelegramCode] = useState('');
  const [telegramPassword, setTelegramPassword] = useState('');
  const [telegramSessionHex, setTelegramSessionHex] = useState<string | null>(null);
  const [telegramDialogs, setTelegramDialogs] = useState<TelegramDialogItem[]>([]);
  const [telegramSelectedIds, setTelegramSelectedIds] = useState<Set<string>>(new Set());
  const [telegramConnectionName, setTelegramConnectionName] = useState('');
  const [telegramLoading, setTelegramLoading] = useState(false);
  const [telegramError, setTelegramError] = useState<string | null>(null);
  /** Timestamp (ms) hasta el que no se puede pedir otro código (cooldown). */
  const [telegramSendCodeBlockedUntil, setTelegramSendCodeBlockedUntil] = useState<number>(0);

  useEffect(() => {
    if (!user || !stackApp) return;
    fetchSources(user, stackApp, setSources, setError, setLoading);
  }, [user, stackApp]);

  const [sendCodeCooldownSecs, setSendCodeCooldownSecs] = useState(0);
  useEffect(() => {
    if (telegramSendCodeBlockedUntil <= Date.now()) {
      setSendCodeCooldownSecs(0);
      return;
    }
    const tick = () => {
      const remaining = Math.ceil((telegramSendCodeBlockedUntil - Date.now()) / 1000);
      setSendCodeCooldownSecs(Math.max(0, remaining));
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [telegramSendCodeBlockedUntil]);

  const refetch = () => {
    if (user && stackApp) fetchSources(user, stackApp, setSources, setError, () => {});
  };

  const handleAddPs3838 = async () => {
    if (!user || !stackApp) return;
    const name = ps3838Name.trim();
    const username = ps3838User.trim();
    const password = ps3838Password;
    if (!name) {
      setPs3838FormError('El nombre es obligatorio.');
      return;
    }
    if (!username) {
      setPs3838FormError('El usuario API es obligatorio.');
      return;
    }
    if (!password) {
      setPs3838FormError('La contraseña API es obligatoria.');
      return;
    }
    setPs3838FormError(null);
    setPs3838Submitting(true);
    const api = initApiClient(createTokenGetter(user, stackApp));
    try {
      await api.post('/external-data-sources', {
        name,
        connector_type: 'ps3838',
        connector_config: { username, password },
      });
      toast.success('Cuenta PS3838 creada.');
      setPs3838Name('');
      setPs3838User('');
      setPs3838Password('');
      setPs3838Open(false);
      refetch();
    } catch (err: unknown) {
      const msg = err && typeof err === 'object' && 'message' in err ? String((err as { message: string }).message) : 'Error al crear cuenta';
      setPs3838FormError(msg);
      toast.error(msg);
    } finally {
      setPs3838Submitting(false);
    }
  };

  const handleTelegramSendCode = async () => {
    if (!user || !stackApp || !telegramPhone.trim()) return;
    if (Date.now() < telegramSendCodeBlockedUntil) return;
    setTelegramError(null);
    setTelegramLoading(true);
    const api = initApiClient(createTokenGetter(user, stackApp));
    try {
      const res = await api.post<{ phone_code_hash?: string; session_pending_hex?: string }>('/telegram/send-code', {
        phone: telegramPhone.trim(),
      });
      if (!res?.phone_code_hash || !res?.session_pending_hex) {
        setTelegramError('Respuesta inesperada del servidor.');
        return;
      }
      setTelegramPhoneCodeHash(res.phone_code_hash);
      setTelegramSessionPendingHex(res.session_pending_hex);
      setTelegramStep('code');
      setTelegramSendCodeBlockedUntil(Date.now() + SEND_CODE_COOLDOWN_SECONDS * 1000);
      toast.success('Código enviado. Revisa Telegram. El código expira en ~5 min.');
    } catch (err: unknown) {
      let msg = 'Error al enviar código';
      let blockSeconds = SEND_CODE_COOLDOWN_SECONDS;
      if (err instanceof ApiResponseError && err.statusCode === 429) {
        try {
          const parsed = JSON.parse(err.message) as { message?: string; retry_after_seconds?: number };
          if (typeof parsed.message === 'string') msg = parsed.message;
          if (typeof parsed.retry_after_seconds === 'number') blockSeconds = parsed.retry_after_seconds;
        } catch {
          /* ignore */
        }
        setTelegramSendCodeBlockedUntil(Date.now() + blockSeconds * 1000);
      } else if (err && typeof err === 'object' && 'message' in err) {
        msg = String((err as { message: string }).message);
      }
      setTelegramError(msg);
      toast.error(msg);
    } finally {
      setTelegramLoading(false);
    }
  };

  const handleTelegramSignIn = async () => {
    if (!user || !stackApp || !telegramCode.trim() || !telegramPhoneCodeHash || !telegramSessionPendingHex) return;
    setTelegramError(null);
    setTelegramLoading(true);
    const api = initApiClient(createTokenGetter(user, stackApp));
    try {
      const res = await api.post<{ session_encrypted?: string }>('/telegram/sign-in', {
        phone: telegramPhone.trim(),
        code: telegramCode.trim(),
        phone_code_hash: telegramPhoneCodeHash,
        session_pending_hex: telegramSessionPendingHex,
        password: telegramPassword || undefined,
      });
      const hex = res?.session_encrypted;
      if (!hex) {
        setTelegramError('No se recibió la sesión.');
        return;
      }
      setTelegramSessionHex(hex);
      setTelegramStep('chats');
      const dialogsRes = await api.post<TelegramDialogItem[]>('/telegram/dialogs', {
        session_encrypted_hex: hex,
      });
      setTelegramDialogs(Array.isArray(dialogsRes) ? dialogsRes : []);
      setTelegramSelectedIds(new Set());
      toast.success('Sesión iniciada. Elige los grupos a monitorear.');
    } catch (err: unknown) {
      const msg = err && typeof err === 'object' && 'message' in err ? String((err as { message: string }).message) : 'Error al iniciar sesión';
      setTelegramError(msg);
      toast.error(msg);
    } finally {
      setTelegramLoading(false);
    }
  };

  const handleTelegramSaveConnection = async () => {
    if (!user || !stackApp || !telegramSessionHex) return;
    const name = telegramConnectionName.trim();
    if (!name) {
      toast.error('Indica un nombre para esta conexión.');
      return;
    }
    setTelegramError(null);
    setTelegramLoading(true);
    const api = initApiClient(createTokenGetter(user, stackApp));
    try {
      await api.post('/telegram/save-connection', {
        name,
        session_encrypted_hex: telegramSessionHex,
        monitored_chats: Array.from(telegramSelectedIds),
      });
      toast.success('Conexión Telegram guardada.');
      setTelegramOpen(false);
      resetTelegramState();
      refetch();
    } catch (err: unknown) {
      const msg = err && typeof err === 'object' && 'message' in err ? String((err as { message: string }).message) : 'Error al guardar';
      setTelegramError(msg);
      toast.error(msg);
    } finally {
      setTelegramLoading(false);
    }
  };

  function resetTelegramState() {
    setTelegramStep('phone');
    setTelegramPhone('');
    setTelegramPhoneCodeHash(null);
    setTelegramSessionPendingHex(null);
    setTelegramSendCodeBlockedUntil(0);
    setTelegramCode('');
    setTelegramPassword('');
    setTelegramSessionHex(null);
    setTelegramDialogs([]);
    setTelegramSelectedIds(new Set());
    setTelegramConnectionName('');
    setTelegramError(null);
  }

  const toggleTelegramChat = (id: string) => {
    setTelegramSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  if (!user) return null;

  const ps3838 = sources.filter((s) => s.connector_type === 'ps3838');
  const telegram = sources.filter((s) => s.connector_type === 'telegram');
  const other = sources.filter((s) => s.connector_type !== 'ps3838' && s.connector_type !== 'telegram');

  return (
    <Layout>
      <div className="space-y-6 w-full max-w-3xl mx-auto pb-12">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Cuentas y fuentes de datos</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Cuentas PS3838 y conexiones Telegram que puedes usar en estrategias como Telegram Tipsters → PS3838.
          </p>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-12 gap-3">
            <LoadingSpinner />
            <p className="text-sm text-muted-foreground">Cargando cuentas…</p>
          </div>
        ) : error ? (
          <Card className="border-destructive/50">
            <CardContent className="pt-6">
              <p className="text-sm text-destructive">{error}</p>
            </CardContent>
          </Card>
        ) : (
          <>
            <Card>
              <CardHeader className="pb-2 flex flex-row items-center justify-between">
                <CardTitle className="text-base flex items-center gap-2">
                  <Link2 className="h-5 w-5 text-primary" />
                  Cuentas PS3838
                </CardTitle>
                <Button variant="outline" size="sm" onClick={() => { setPs3838Open(true); setPs3838FormError(null); }}>
                  <Plus className="h-4 w-4 mr-1" />
                  Añadir cuenta
                </Button>
              </CardHeader>
              <CardContent className="space-y-2">
                {ps3838.length === 0 ? (
                  <div className="space-y-3">
                    <p className="text-sm text-muted-foreground">
                      No tienes ninguna cuenta PS3838. Añade una para usarla en la estrategia Telegram Tipsters.
                    </p>
                    <p className="text-sm text-foreground">
                      ¿Necesitas una cuenta? <strong>Regístrate gratis</strong> en Betinasia (plataforma PS3838): cuotas competitivas, API para automatizar y soporte para estrategias de tipsters.
                    </p>
                    <Button variant="outline" size="sm" asChild>
                      <a href="https://portal.betinasia.com/Account/RegisterCustomer?rafid=6ce7d6d3-7449-4da9-9b1a-4c209fb9b100" target="_blank" rel="noopener noreferrer">
                        Crear cuenta PS3838 →
                      </a>
                    </Button>
                  </div>
                ) : (
                  ps3838.map((s) => (
                    <div
                      key={s.id}
                      className="flex items-center justify-between py-2 px-3 rounded-lg bg-muted/50"
                    >
                      <span className="font-medium">{s.name}</span>
                      <Badge variant={s.is_active ? 'default' : 'secondary'}>
                        {s.is_active ? 'Activa' : 'Inactiva'}
                      </Badge>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2 flex flex-row items-center justify-between">
                <CardTitle className="text-base flex items-center gap-2">
                  <MessageSquare className="h-5 w-5 text-primary" />
                  Conexiones Telegram
                </CardTitle>
                <Button variant="outline" size="sm" onClick={() => { setTelegramOpen(true); resetTelegramState(); }}>
                  <Plus className="h-4 w-4 mr-1" />
                  Conectar Telegram
                </Button>
              </CardHeader>
              <CardContent className="space-y-2">
                {telegram.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No tienes ninguna conexión Telegram. Conecta tu cuenta para seguir grupos de tipsters.
                  </p>
                ) : (
                  telegram.map((s) => (
                    <div
                      key={s.id}
                      className="flex items-center justify-between py-2 px-3 rounded-lg bg-muted/50"
                    >
                      <span className="font-medium">{s.name}</span>
                      <Badge variant={s.is_active ? 'default' : 'secondary'}>
                        {s.is_active ? 'Conectada' : 'Inactiva'}
                      </Badge>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>

            {other.length > 0 && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Otras fuentes</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {other.map((s) => (
                    <div
                      key={s.id}
                      className="flex items-center justify-between py-2 px-3 rounded-lg bg-muted/50"
                    >
                      <span className="font-medium">{s.name}</span>
                      <Badge variant="outline">{s.connector_type}</Badge>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}

            <Card className="border-primary/30 bg-primary/5">
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground mb-3">
                  Para usar la estrategia Telegram Tipsters → PS3838 necesitas una cuenta PS3838 y una conexión Telegram.
                  ¿Sin cuenta?{' '}
                  <a
                    href="https://portal.betinasia.com/Account/RegisterCustomer?rafid=6ce7d6d3-7449-4da9-9b1a-4c209fb9b100"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary underline hover:no-underline font-medium"
                  >
                    Regístrate gratis en Betinasia
                  </a>
                </p>
                <p className="text-xs text-muted-foreground mb-3">
                  Para recibir tips en tiempo real desde los grupos, ejecuta en el backend:{' '}
                  <code className="bg-muted px-1 rounded">python -m app.workers.telegram_listener_worker --discover</code>
                </p>
                <Button asChild variant="default" size="sm">
                  <Link href="/strategies/create?template=telegram_tipster_ps3838">
                    Crear estrategia Telegram Tipsters
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </Link>
                </Button>
              </CardContent>
            </Card>
          </>
        )}
      </div>

      {/* Dialog: Añadir cuenta PS3838 */}
      <Dialog open={ps3838Open} onOpenChange={setPs3838Open}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Añadir cuenta PS3838</DialogTitle>
            <DialogDescription asChild>
              <div className="space-y-2">
                <p>Usuario y contraseña de la API de PS3838. La cuenta debe estar financiada.</p>
                <p className="text-xs">
                  ¿Aún no tienes cuenta?{' '}
                  <a
                    href="https://portal.betinasia.com/Account/RegisterCustomer?rafid=6ce7d6d3-7449-4da9-9b1a-4c209fb9b100"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary underline hover:no-underline font-medium"
                  >
                    Regístrate gratis en Betinasia
                  </a>
                  {' '}— cuotas competitivas y API lista para automatizar tus estrategias.
                </p>
              </div>
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-2">
            <div>
              <Label htmlFor="ps3838-name">Nombre</Label>
              <Input
                id="ps3838-name"
                value={ps3838Name}
                onChange={(e) => setPs3838Name(e.target.value)}
                placeholder="Ej. Mi cuenta principal"
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="ps3838-user">Usuario API</Label>
              <Input
                id="ps3838-user"
                value={ps3838User}
                onChange={(e) => setPs3838User(e.target.value)}
                placeholder="Usuario"
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="ps3838-password">Contraseña API</Label>
              <Input
                id="ps3838-password"
                type="password"
                value={ps3838Password}
                onChange={(e) => setPs3838Password(e.target.value)}
                placeholder="Contraseña"
                className="mt-1"
              />
            </div>
            {ps3838FormError && (
              <p className="text-sm text-destructive">{ps3838FormError}</p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPs3838Open(false)}>Cancelar</Button>
            <Button onClick={handleAddPs3838} disabled={ps3838Submitting}>
              {ps3838Submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Guardar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Conectar Telegram (multi-step) */}
      <Dialog open={telegramOpen} onOpenChange={(open) => { if (!open) resetTelegramState(); setTelegramOpen(open); }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Conectar cuenta Telegram</DialogTitle>
            <DialogDescription>
              {telegramStep === 'phone' && 'Introduce tu número con código de país (ej. +34600000000).'}
              {telegramStep === 'code' && 'Introduce el código de 5 dígitos que has recibido en Telegram. Si tienes 2FA, añade la contraseña.'}
              {telegramStep === 'chats' && 'Selecciona los grupos o canales que quieres monitorear para tips.'}
              {telegramStep === 'save' && 'Asigna un nombre a esta conexión y guarda.'}
            </DialogDescription>
          </DialogHeader>
          <div className="py-2">
            {telegramStep === 'phone' && (
              <div className="space-y-4">
                <div>
                  <Label htmlFor="tg-phone">Teléfono</Label>
                  <Input
                    id="tg-phone"
                    value={telegramPhone}
                    onChange={(e) => setTelegramPhone(e.target.value)}
                    placeholder="+34600000000"
                    className="mt-1"
                  />
                </div>
                <Button onClick={handleTelegramSendCode} disabled={telegramLoading}>
                  {telegramLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                  Enviar código
                </Button>
              </div>
            )}
            {telegramStep === 'code' && (
              <div className="space-y-4">
                <p className="text-xs text-muted-foreground">
                  El código expira en ~5 min. Si no lo recibes o expiró, solicita uno nuevo (espera 2 min entre intentos).
                </p>
                <div>
                  <Label htmlFor="tg-code">Código</Label>
                  <Input
                    id="tg-code"
                    value={telegramCode}
                    onChange={(e) => setTelegramCode(e.target.value)}
                    placeholder="12345"
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label htmlFor="tg-2fa">Contraseña 2FA (opcional)</Label>
                  <Input
                    id="tg-2fa"
                    type="password"
                    value={telegramPassword}
                    onChange={(e) => setTelegramPassword(e.target.value)}
                    placeholder="Si tienes verificación en dos pasos"
                    className="mt-1"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <Button onClick={handleTelegramSignIn} disabled={telegramLoading}>
                    {telegramLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                    Iniciar sesión
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleTelegramSendCode}
                    disabled={telegramLoading || sendCodeCooldownSecs > 0}
                  >
                    {sendCodeCooldownSecs > 0
                      ? `Solicitar nuevo código en ${Math.floor(sendCodeCooldownSecs / 60)}:${String(sendCodeCooldownSecs % 60).padStart(2, '0')}`
                      : 'Solicitar nuevo código'}
                  </Button>
                </div>
              </div>
            )}
            {telegramStep === 'chats' && (
              <div className="space-y-3 max-h-64 overflow-y-auto">
                {telegramDialogs.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No hay grupos o canales.</p>
                ) : (
                  telegramDialogs.map((d) => (
                    <label key={d.id} className="flex items-center gap-2 cursor-pointer rounded p-2 hover:bg-muted/50">
                      <input
                        type="checkbox"
                        checked={telegramSelectedIds.has(d.id)}
                        onChange={() => toggleTelegramChat(d.id)}
                        className="rounded"
                      />
                      <span className="text-sm font-medium truncate">{d.title}</span>
                      {d.is_channel && <Badge variant="outline" className="text-xs">Canal</Badge>}
                    </label>
                  ))
                )}
                <div className="flex gap-2 pt-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setTelegramConnectionName('');
                      setTelegramStep('save');
                    }}
                  >
                    Siguiente
                  </Button>
                </div>
              </div>
            )}
            {telegramStep === 'save' && (
              <div className="space-y-4">
                <div>
                  <Label htmlFor="tg-name">Nombre de la conexión</Label>
                  <Input
                    id="tg-name"
                    value={telegramConnectionName}
                    onChange={(e) => setTelegramConnectionName(e.target.value)}
                    placeholder="Ej. Telegram tipsters"
                    className="mt-1"
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  {telegramSelectedIds.size} chat(s) seleccionado(s).
                </p>
                <div className="flex gap-2">
                  <Button variant="outline" onClick={() => setTelegramStep('chats')}>Atrás</Button>
                  <Button onClick={handleTelegramSaveConnection} disabled={telegramLoading}>
                    {telegramLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                    Guardar conexión
                  </Button>
                </div>
              </div>
            )}
            {telegramError && (
              <p className="text-sm text-destructive mt-2">{telegramError}</p>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </Layout>
  );
}
