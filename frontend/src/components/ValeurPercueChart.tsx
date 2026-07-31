"use client";

import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
} from "chart.js";
import { Bar } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip);

export type ValeurPoint = { nom: string; score: number };

export default function ValeurPercueChart({ data }: { data: ValeurPoint[] }) {
  return (
    <Bar
      data={{
        labels: data.map((d) => d.nom),
        datasets: [
          {
            label: "Score de valeur ajusté",
            data: data.map((d) => d.score),
            backgroundColor: "#34d399",
          },
        ],
      }}
      options={{
        indexAxis: "y" as const,
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { title: { display: true, text: "Score de valeur ajusté" } },
        },
      }}
    />
  );
}
