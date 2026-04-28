import React, { useState, useEffect } from 'react';

// --- Types ---
interface TeamStanding {
  name: string;
  matches: number;
  wins: number;
  losses: number;
  points: number;
  nrr: number;
}

interface SimulationResult {
  name: string;
  top4_probability: number;
  top2_probability: number;
  avg_position: number;
  current_points: number;
  current_nrr: number;
}

interface SimulationResponse {
  teams: SimulationResult[];
  simulations_run: number;
  remaining_matches: number;
  elapsed_seconds: number;
}

// --- Components ---

const Header = () => (
  <header className="bg-surface-container-lowest/90 backdrop-blur-md sticky top-0 z-50 border-b border-outline-variant flex items-center justify-between px-6 py-3 w-full">
    <div className="flex items-center gap-2 text-primary">
      <span className="material-symbols-outlined">sports_cricket</span>
      <span className="text-lg font-bold text-on-surface font-headline tracking-tight">IPL Playoff Engine</span>
    </div>
    <nav className="hidden md:flex items-center gap-4">
      <a className="flex items-center gap-2 px-3 py-1.5 rounded-md text-primary font-bold hover:bg-surface-variant transition-colors" href="#">
        <span className="material-symbols-outlined text-sm" style={{ fontVariationSettings: "'FILL' 1" }}>dashboard</span>
        <span className="text-sm">Dashboard</span>
      </a>
      <a className="flex items-center gap-2 px-3 py-1.5 rounded-md text-on-surface-variant hover:text-on-surface hover:bg-surface-variant transition-colors" href="#">
        <span className="material-symbols-outlined text-sm">science</span>
        <span className="text-sm">Scenarios</span>
      </a>
      <a className="flex items-center gap-2 px-3 py-1.5 rounded-md text-on-surface-variant hover:text-on-surface hover:bg-surface-variant transition-colors" href="#">
        <span className="material-symbols-outlined text-sm">leaderboard</span>
        <span className="text-sm">Stats</span>
      </a>
      <a className="flex items-center gap-2 px-3 py-1.5 rounded-md text-on-surface-variant hover:text-on-surface hover:bg-surface-variant transition-colors" href="#">
        <span className="material-symbols-outlined text-sm">settings</span>
        <span className="text-sm">Settings</span>
      </a>
    </nav>
    <button className="text-primary hover:bg-surface-variant p-2 rounded-full transition-colors active:scale-95 duration-150 flex items-center justify-center">
      <span className="material-symbols-outlined">refresh</span>
    </button>
  </header>
);

const BottomNav = () => (
  <nav className="md:hidden fixed bottom-0 w-full z-50 bg-[#0c0c0f] border-t border-[#27272a] pb-safe flex justify-around items-center h-16 px-2">
    <a className="flex flex-col items-center justify-center text-[#a78bfa] font-bold tap-highlight-transparent w-full h-full" href="#">
      <span className="material-symbols-outlined text-xl mb-1" style={{ fontVariationSettings: "'FILL' 1" }}>dashboard</span>
      <span className="text-[11px] font-medium font-geist">Dashboard</span>
    </a>
    <a className="flex flex-col items-center justify-center text-[#a1a1aa] hover:text-[#fafafa] tap-highlight-transparent w-full h-full transition-colors" href="#">
      <span className="material-symbols-outlined text-xl mb-1">science</span>
      <span className="text-[11px] font-medium font-geist">Scenarios</span>
    </a>
    <a className="flex flex-col items-center justify-center text-[#a1a1aa] hover:text-[#fafafa] tap-highlight-transparent w-full h-full transition-colors" href="#">
      <span className="material-symbols-outlined text-xl mb-1">leaderboard</span>
      <span className="text-[11px] font-medium font-geist">Stats</span>
    </a>
    <a className="flex flex-col items-center justify-center text-[#a1a1aa] hover:text-[#fafafa] tap-highlight-transparent w-full h-full transition-colors" href="#">
      <span className="material-symbols-outlined text-xl mb-1">settings</span>
      <span className="text-[11px] font-medium font-geist">Settings</span>
    </a>
  </nav>
);

// Helper for Team Abbreviations and Colors
const teamMeta: Record<string, { abbr: string, colorClass: string }> = {
  "Chennai Super Kings": { abbr: "CSK", colorClass: "bg-primary/20 text-primary" },
  "Mumbai Indians": { abbr: "MI", colorClass: "bg-primary/20 text-primary" },
  "Rajasthan Royals": { abbr: "RR", colorClass: "bg-secondary/20 text-secondary-fixed" },
  "Royal Challengers Bengaluru": { abbr: "RCB", colorClass: "bg-secondary/20 text-secondary-fixed" },
  "Kolkata Knight Riders": { abbr: "KKR", colorClass: "bg-secondary/20 text-secondary-fixed" },
  "Sunrisers Hyderabad": { abbr: "SRH", colorClass: "bg-secondary/20 text-secondary-fixed" },
  "Delhi Capitals": { abbr: "DC", colorClass: "bg-error/10 text-error" },
  "Lucknow Super Giants": { abbr: "LSG", colorClass: "bg-error/10 text-error" },
  "Gujarat Titans": { abbr: "GT", colorClass: "bg-error/10 text-error" },
  "Punjab Kings": { abbr: "PBKS", colorClass: "bg-error/10 text-error" }
};

const getTeamMeta = (name: string) => teamMeta[name] || { abbr: name.substring(0, 3).toUpperCase(), colorClass: "bg-surface-variant text-on-surface-variant" };

const LiveInsights = ({ teams }: { teams: SimulationResult[] }) => {
  // Take top 5 for the chart
  const topTeams = teams.slice(0, 5);

  return (
    <section className="bg-surface-container border border-outline-variant rounded-lg p-5 flex flex-col gap-6 shadow-sm">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-on-surface font-headline tracking-tight">Live Insights: Top 4 Probability</h2>
        <span className="text-xs font-medium text-tertiary bg-tertiary/10 px-2 py-1 rounded-full border border-tertiary/20 flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-tertiary animate-pulse"></span>
          Live
        </span>
      </div>
      <div className="h-64 flex items-end gap-2 md:gap-8 w-full pb-6 border-b border-outline-variant relative mt-2 pl-8">
        <div className="absolute left-0 top-0 h-full flex flex-col justify-between text-[10px] text-on-surface-variant pb-6 pr-2 text-right w-8">
          <span>100</span><span>75</span><span>50</span><span>25</span><span>0</span>
        </div>
        {topTeams.map((team, index) => {
          const prob = Math.round(team.top4_probability * 100);
          const meta = getTeamMeta(team.name);
          let barColor = "bg-secondary";
          let barBgColor = "bg-secondary/10";
          let borderColor = "border-secondary/20";
          let textColor = "text-primary-fixed-dim";
          
          if (prob > 75) {
            barColor = "bg-primary";
            barBgColor = "bg-primary/10";
            borderColor = "border-primary/20";
            textColor = "text-tertiary";
          } else if (prob < 25) {
            barColor = "bg-error";
            barBgColor = "bg-error/10";
            borderColor = "border-error/20";
            textColor = "text-error";
          }

          return (
            <div key={team.name} className="flex-1 flex flex-col items-center justify-end h-full group relative">
              <div className={`w-full max-w-[60px] ${barBgColor} rounded-t-sm relative flex items-end justify-center border ${borderColor} transition-colors`} style={{ height: `${prob}%` }}>
                <div className={`w-full ${barColor} rounded-t-sm absolute bottom-0 left-0 opacity-80`} style={{ height: '100%' }}></div>
                <span className={`absolute -top-6 text-xs font-bold ${textColor}`}>{prob}%</span>
              </div>
              <span className="text-xs font-medium text-on-surface-variant mt-3 uppercase tracking-wider">{meta.abbr}</span>
            </div>
          );
        })}
      </div>
    </section>
  );
};

const TeamStandings = ({ teams }: { teams: SimulationResult[] }) => {
  return (
    <section className="lg:col-span-2 bg-surface-container border border-outline-variant rounded-lg flex flex-col overflow-hidden">
      <div className="p-5 border-b border-outline-variant flex items-center justify-between bg-surface-container-lowest/50">
        <h2 className="text-lg font-semibold text-on-surface font-headline tracking-tight">Team Standings</h2>
        <button className="text-xs font-medium text-primary hover:text-primary-fixed transition-colors flex items-center gap-1">
          Detailed View <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
        </button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-surface text-on-surface-variant text-xs uppercase tracking-wider border-b border-outline-variant">
            <tr>
              <th className="py-4 px-5 font-medium">Franchise</th>
              <th className="py-4 px-5 font-medium">Top 4 %</th>
              <th className="py-4 px-5 font-medium">Top 2 %</th>
              <th className="py-4 px-5 font-medium">Avg Pos</th>
              <th className="py-4 px-5 font-medium text-right">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-outline-variant text-on-surface">
            {teams.map((team) => {
              const prob = team.top4_probability * 100;
              const meta = getTeamMeta(team.name);
              
              let statusText = "In Hunt";
              let statusClass = "bg-surface-variant text-on-surface-variant border-outline-variant";
              let probColor = "text-primary-fixed-dim";

              if (prob > 90) {
                statusText = "Qualified";
                statusClass = "bg-tertiary/10 text-tertiary border-tertiary/20";
                probColor = "text-tertiary";
              } else if (prob > 75) {
                statusText = "Likely";
                statusClass = "bg-tertiary/10 text-tertiary border-tertiary/20";
                probColor = "text-tertiary";
              } else if (prob < 20) {
                statusText = "Critical";
                statusClass = "bg-error/10 text-error border-error/20";
                probColor = "text-error";
              }

              return (
                <tr key={team.name} className="hover:bg-surface-variant/50 transition-colors group">
                  <td className="py-4 px-5 font-medium flex items-center gap-3">
                    <div className={`w-6 h-6 rounded flex items-center justify-center text-[10px] font-bold ${meta.colorClass}`}>
                      {meta.abbr}
                    </div>
                    {team.name}
                  </td>
                  <td className={`py-4 px-5 font-bold tracking-tight ${probColor}`}>{prob.toFixed(1)}%</td>
                  <td className="py-4 px-5 text-on-surface-variant">{(team.top2_probability * 100).toFixed(1)}%</td>
                  <td className="py-4 px-5 text-on-surface-variant">{team.avg_position.toFixed(1)}</td>
                  <td className="py-4 px-5 text-right">
                    <span className={`inline-flex items-center px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider border ${statusClass}`}>
                      {statusText}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
};

const ScenarioSimulator = ({ onSimulate, isSimulating }: { onSimulate: () => void, isSimulating: boolean }) => {
  return (
    <section className="lg:col-span-1 bg-surface-container border border-outline-variant rounded-lg p-5 flex flex-col relative overflow-hidden">
      <div className="absolute -top-24 -right-24 w-48 h-48 bg-primary/5 rounded-full blur-3xl pointer-events-none"></div>
      <div className="flex items-center gap-2 mb-2">
        <span className="material-symbols-outlined text-primary text-xl">science</span>
        <h2 className="text-lg font-semibold text-on-surface font-headline tracking-tight">Scenario Simulator</h2>
      </div>
      <p className="text-sm text-on-surface-variant mb-8 leading-relaxed">Adjust upcoming match results to simulate shifts in global playoff probabilities.</p>
      
      <div className="space-y-5 flex-1 relative z-10">
        <div>
          <label className="block text-[11px] uppercase tracking-wider font-semibold text-on-surface-variant mb-2">Select Match</label>
          <div className="relative group">
            <select className="w-full bg-surface border border-outline-variant text-on-surface text-sm rounded-md focus:ring-2 focus:ring-primary/50 focus:border-primary block p-3 appearance-none transition-all group-hover:border-primary/50">
              <option>Match 45: CSK vs MI</option>
              <option>Match 46: RR vs RCB</option>
              <option>Match 47: GT vs LSG</option>
            </select>
            <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none text-on-surface-variant">
              <span className="material-symbols-outlined text-sm">expand_more</span>
            </div>
          </div>
        </div>
        <div>
          <label className="block text-[11px] uppercase tracking-wider font-semibold text-on-surface-variant mb-2">Projected Winner</label>
          <div className="relative group">
            <select className="w-full bg-surface border border-outline-variant text-on-surface text-sm rounded-md focus:ring-2 focus:ring-primary/50 focus:border-primary block p-3 appearance-none transition-all group-hover:border-primary/50">
              <option>Chennai Super Kings</option>
              <option>Mumbai Indians</option>
            </select>
            <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none text-on-surface-variant">
              <span className="material-symbols-outlined text-sm">expand_more</span>
            </div>
          </div>
        </div>
      </div>
      
      <button 
        onClick={onSimulate}
        disabled={isSimulating}
        className="w-full mt-8 bg-primary hover:bg-primary-fixed text-on-primary font-bold py-3 px-4 rounded-md transition-colors flex items-center justify-center gap-2 active:scale-[0.98] shadow-[0_0_15px_rgba(167,139,250,0.15)] disabled:opacity-50 disabled:cursor-not-allowed">
        {isSimulating ? (
          <span className="material-symbols-outlined text-sm animate-spin">sync</span>
        ) : (
          <span className="material-symbols-outlined text-sm" style={{ fontVariationSettings: "'FILL' 1" }}>calculate</span>
        )}
        {isSimulating ? 'Recalculating...' : 'Recalculate Odds'}
      </button>
    </section>
  );
};

export default function App() {
  const [data, setData] = useState<SimulationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [isSimulating, setIsSimulating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSimulation = async () => {
    try {
      setIsSimulating(true);
      setError(null);
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/simulate?simulations=1000`);
      if (!response.ok) {
        throw new Error('Failed to fetch simulation data');
      }
      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      setLoading(false);
      setIsSimulating(false);
    }
  };

  useEffect(() => {
    fetchSimulation();
  }, []);

  return (
    <>
      <Header />
      
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 lg:p-8 flex flex-col gap-6 pb-24 md:pb-8">
        {loading && !data ? (
          <div className="flex items-center justify-center h-64 text-on-surface-variant">
            <span className="material-symbols-outlined animate-spin mr-2">sync</span>
            Loading simulation data...
          </div>
        ) : error ? (
          <div className="bg-error-container text-on-error-container p-4 rounded-lg flex items-center gap-2">
             <span className="material-symbols-outlined">error</span>
             {error}
          </div>
        ) : data ? (
          <>
            <LiveInsights teams={data.teams} />
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <TeamStandings teams={data.teams} />
              <ScenarioSimulator onSimulate={fetchSimulation} isSimulating={isSimulating} />
            </div>
            <div className="text-xs text-on-surface-variant text-center mt-4">
              Simulations run: {data.simulations_run} | Remaining matches: {data.remaining_matches} | Time: {data.elapsed_seconds.toFixed(2)}s
            </div>
          </>
        ) : null}
      </main>

      <BottomNav />
    </>
  );
}
