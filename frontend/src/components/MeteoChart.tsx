"use client";

import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
  Legend,
} from "chart.js";
import { Bar } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

export type MeteoPoint = { ville: string; beauTemps: number | null; pluie: number | null };

export default function MeteoChart({ data }: { data: MeteoPoint[] }) {
  return (
    <Bar
      data={{
        labels: data.map((d) => d.ville),
        datasets: [
          {
            label: "Beau temps",
            data: data.map((d) => d.beauTemps),
            backgroundColor: "#fbbf24",
          },
          {
            label: "Pluie",
            data: data.map((d) => d.pluie),
            backgroundColor: "#3b82f6",
          },
        ],
      }}
      options={{
        responsive: true,
        plugins: {
          legend: { position: "top" as const },
          title: { display: false },
        },
        scales: {
          y: {
            beginAtZero: true,
            title: { display: true, text: "Check-ins moyens / jour" },
          },
        },
      }}
    />
  );
}
