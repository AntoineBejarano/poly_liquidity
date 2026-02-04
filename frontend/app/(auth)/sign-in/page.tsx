import { SignIn } from '@stackframe/stack';

export default function SignInPage() {
  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-slate-950 text-slate-100">
      <div className="w-full max-w-md">
        <div className="rounded-2xl p-8 shadow-premium-lg animate-fade-in bg-black/90 border border-white/10">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl gradient-premium mb-4 shadow-lg">
              <span className="text-3xl font-bold text-white">A</span>
            </div>
            <h1 className="text-3xl font-bold text-slate-100 mb-2">
              AlphaEdge
            </h1>
            <p className="text-slate-300 text-sm">
              Sistema de trading institucional de alta frecuencia
            </p>
          </div>
          <div className="mt-6">
            <SignIn />
          </div>
        </div>
        <p className="text-center text-xs text-slate-400 mt-6">
          Plataforma profesional para gestión de liquidez en mercados de predicción
        </p>
      </div>
    </div>
  );
}

