'use client';

import { useState } from 'react';
import { useUser } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import Link from 'next/link';

export default function SettingsPage() {
  return (
    <Layout>
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Configuración</h1>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <SettingsCard
            title="Riesgo"
            description="Configuración de límites de riesgo y exposición"
            href="/risk"
            icon="⚠️"
          />
          <SettingsCard
            title="Sistema"
            description="Configuración del sistema y parámetros operativos"
            href="/settings/system"
            icon="⚙️"
          />
          <SettingsCard
            title="Wallets"
            description="Gestión de wallets y claves privadas"
            href="/settings/wallets"
            icon="💼"
          />
          <SettingsCard
            title="Checkers"
            description="Configuración de checkers y credenciales"
            href="/settings/checkers"
            icon="🔍"
          />
        </div>
      </div>
    </Layout>
  );
}

function SettingsCard({
  title,
  description,
  href,
  icon,
}: {
  title: string;
  description: string;
  href: string;
  icon: string;
}) {
  return (
    <Link href={href}>
      <div className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow cursor-pointer">
        <div className="flex items-start">
          <span className="text-3xl mr-4">{icon}</span>
          <div>
            <h3 className="text-xl font-semibold mb-2">{title}</h3>
            <p className="text-gray-600 text-sm">{description}</p>
          </div>
        </div>
      </div>
    </Link>
  );
}

