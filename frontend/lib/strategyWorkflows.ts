/**
 * Workflows user-friendly por plantilla.
 * Describe el flujo de cada estrategia en lenguaje claro para que el usuario entienda qué hace.
 */

export interface WorkflowStep {
  title: string;
  description: string;
}

export const STRATEGY_WORKFLOWS: Record<string, WorkflowStep[]> = {
  telegram_tipster_ps3838: [
    { title: 'Escuchamos tus grupos de Telegram', description: 'Los mensajes de los tipsters llegan en tiempo real.' },
    { title: 'Extraemos los tips', description: 'Partido, selección, stake y odds del mensaje.' },
    { title: 'Buscamos el partido en PS3838', description: 'Resolvemos el evento y verificamos que las odds coinciden.' },
    { title: 'Aplicamos tus límites de riesgo', description: 'max_stake por tip, max diario, clasificación.' },
    { title: 'Apostamos (o te preguntamos)', description: 'Según el modo: automático o con confirmación previa.' },
  ],
  surebet_polymarket_pinnacle: [
    { title: 'Escaneamos mercados', description: 'Polymarket y Pinnacle en paralelo.' },
    { title: 'Detectamos surebets', description: 'Oportunidades donde comprar barato y vender caro.' },
    { title: 'Validamos profit mínimo', description: 'Solo ejecutamos si supera tu % configurado.' },
    { title: 'Ejecutamos las órdenes', description: 'Compra en un venue, venta en el otro.' },
    { title: 'Monitorizamos el fill', description: 'Hasta que se complete o expire.' },
  ],
  liquidity_near_end: [
    { title: 'Detectamos eventos terminados', description: 'Partidos que ya acabaron en el mundo real.' },
    { title: 'Esperamos resolución en Polymarket', description: 'El mercado aún no se ha cerrado.' },
    { title: 'Calculamos el diferencial', description: 'Oportunidad de liquidez near-resolution.' },
    { title: 'Colocamos la orden', description: 'Compra del lado que va a ganar.' },
    { title: 'Cobramos al resolverse', description: 'Cuando Polymarket cierra el mercado.' },
  ],
};
