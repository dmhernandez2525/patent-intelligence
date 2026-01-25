import { Link } from 'react-router-dom'
import { Search, Clock, Lightbulb, TrendingUp, Shield, Zap, Map, Eye, Bell, Database, Globe, Cpu } from 'lucide-react'

function Landing() {
  return (
    <div className="min-h-screen">
      {/* Navigation */}
      <nav className="border-b border-gray-200 bg-white sticky top-0 z-50">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-primary-600 flex items-center justify-center">
                <Zap className="h-5 w-5 text-white" />
              </div>
              <span className="text-xl font-bold text-gray-900">Patent Intelligence</span>
            </div>
            <div className="hidden md:flex items-center gap-6">
              <a href="#features" className="text-sm font-medium text-gray-600 hover:text-gray-900">Features</a>
              <a href="#how-it-works" className="text-sm font-medium text-gray-600 hover:text-gray-900">How It Works</a>
              <a href="#pricing" className="text-sm font-medium text-gray-600 hover:text-gray-900">Pricing</a>
              <Link to="/dashboard" className="text-sm font-medium text-gray-600 hover:text-gray-900">Dashboard</Link>
            </div>
            <div className="flex items-center gap-4">
              <Link
                to="/search"
                className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 transition-colors"
              >
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-b from-primary-50 to-white py-20 sm:py-32">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-3xl text-center">
            <div className="mb-6 inline-flex items-center rounded-full bg-primary-100 px-4 py-1.5 text-sm font-medium text-primary-700">
              AI-Powered Patent Intelligence Platform
            </div>
            <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-6xl">
              Discover What's Expiring, What's Missing, and What's Next
            </h1>
            <p className="mt-6 text-lg leading-8 text-gray-600">
              Search 200M+ patents globally, track expirations, discover white space opportunities,
              and generate AI-powered invention ideas — all in one platform built for innovators.
            </p>
            <div className="mt-10 flex items-center justify-center gap-4 flex-wrap">
              <Link
                to="/search"
                className="rounded-lg bg-primary-600 px-6 py-3 text-base font-semibold text-white shadow-sm hover:bg-primary-700 transition-colors"
              >
                Start Searching Free
              </Link>
              <Link
                to="/dashboard"
                className="rounded-lg border border-gray-300 bg-white px-6 py-3 text-base font-semibold text-gray-700 shadow-sm hover:bg-gray-50 transition-colors"
              >
                View Dashboard
              </Link>
            </div>
          </div>
        </div>

        {/* Floating Feature Pills */}
        <div className="mt-16 flex flex-wrap justify-center gap-3 px-4">
          {['Semantic Search', 'Expiration Alerts', 'White Space Discovery', 'AI Ideas', 'Citation Networks', 'Multi-Source Data'].map((feature) => (
            <span key={feature} className="rounded-full bg-white border border-gray-200 px-4 py-2 text-sm text-gray-700 shadow-sm">
              {feature}
            </span>
          ))}
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="py-20 sm:py-28">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
              Complete Patent Intelligence Suite
            </h2>
            <p className="mt-4 text-lg text-gray-600">
              Every tool you need to find, analyze, and act on patent opportunities.
            </p>
          </div>
          <div className="mx-auto mt-16 grid max-w-6xl grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
            <FeatureCard
              icon={<Search className="h-6 w-6" />}
              title="Semantic Patent Search"
              description="AI-powered search using PatentSBERTa embeddings. Find relevant patents by meaning, not just keywords. Hybrid search combines vector similarity with traditional filters."
              link="/search"
            />
            <FeatureCard
              icon={<Clock className="h-6 w-6" />}
              title="Expiration Tracking"
              description="Real-time monitoring of patent expirations, maintenance fees, and lapsed patents. Get alerts before deadlines and discover newly available technologies."
              link="/expiration"
            />
            <FeatureCard
              icon={<Map className="h-6 w-6" />}
              title="White Space Discovery"
              description="Identify technology gaps and untapped opportunities. Analyze CPC coverage, find declining sectors, and discover cross-domain combination opportunities."
              link="/whitespace"
            />
            <FeatureCard
              icon={<Lightbulb className="h-6 w-6" />}
              title="AI Idea Generation"
              description="LLM-powered invention suggestions from expiring patents, technology trends, and cross-domain combinations. Generate novel, commercially viable concepts."
              link="/ideas"
            />
            <FeatureCard
              icon={<TrendingUp className="h-6 w-6" />}
              title="Trend Analysis"
              description="Technology trajectory mapping with CPC-based trends, filing patterns, and growth areas. Visualize citation networks and identify influential patents."
              link="/trends"
            />
            <FeatureCard
              icon={<Shield className="h-6 w-6" />}
              title="Prior Art Discovery"
              description="Vector-based similarity search for prior art candidates. Find similar patents across jurisdictions and understand the landscape before filing."
              link="/similarity"
            />
            <FeatureCard
              icon={<Eye className="h-6 w-6" />}
              title="Patent Watchlist"
              description="Track patents, CPC codes, and assignees you care about. Get automatic alerts for expirations, maintenance fees, and status changes."
              link="/watchlist"
            />
            <FeatureCard
              icon={<Bell className="h-6 w-6" />}
              title="Smart Alerts"
              description="Configurable notifications for expiring patents, upcoming maintenance fees, and new activity. Priority-based alert system keeps you focused on what matters."
              link="/watchlist"
            />
            <FeatureCard
              icon={<Database className="h-6 w-6" />}
              title="Multi-Source Ingestion"
              description="Unified data from USPTO, EPO, and BigQuery. 200M+ patents from 170+ jurisdictions, continuously updated with latest filings."
              link="/ingestion"
            />
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="border-y border-gray-200 bg-gray-50 py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center mb-16">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
              How It Works
            </h2>
            <p className="mt-4 text-lg text-gray-600">
              From search to strategy in minutes, not months.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <StepCard
              number="1"
              title="Search"
              description="Use semantic or keyword search to find relevant patents across our 200M+ patent database."
            />
            <StepCard
              number="2"
              title="Analyze"
              description="Explore trends, citation networks, and similar patents. Understand the technology landscape."
            />
            <StepCard
              number="3"
              title="Discover"
              description="Find white space opportunities, expiring patents, and technology gaps using AI-powered analysis."
            />
            <StepCard
              number="4"
              title="Act"
              description="Generate invention ideas, track key patents, and get alerts for opportunities that matter."
            />
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-16">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 gap-8 sm:grid-cols-4">
            <StatItem value="200M+" label="Global Patents" icon={<Database className="h-5 w-5" />} />
            <StatItem value="170+" label="Jurisdictions" icon={<Globe className="h-5 w-5" />} />
            <StatItem value="50%" label="Patents Lapse" icon={<Clock className="h-5 w-5" />} />
            <StatItem value="AI" label="Powered Analysis" icon={<Cpu className="h-5 w-5" />} />
          </div>
        </div>
      </section>

      {/* Tech Stack */}
      <section className="border-y border-gray-200 bg-white py-16">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-10">
            <h3 className="text-lg font-semibold text-gray-900">Built With Modern Technology</h3>
          </div>
          <div className="flex flex-wrap justify-center gap-8 items-center opacity-70">
            {['React', 'TypeScript', 'FastAPI', 'PostgreSQL', 'pgvector', 'Redis', 'Claude AI', 'PatentSBERTa'].map((tech) => (
              <span key={tech} className="text-sm font-medium text-gray-600">{tech}</span>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
              Transparent Pricing
            </h2>
            <p className="mt-4 text-lg text-gray-600">
              No hidden fees. No "contact us" walls. Start with what you need.
            </p>
          </div>
          <div className="mx-auto mt-12 grid max-w-4xl grid-cols-1 gap-8 sm:grid-cols-3">
            <PricingCard
              tier="Starter"
              price="$49"
              description="For solo practitioners and researchers"
              features={["1,000 searches/month", "Expiration tracking", "5 watchlist items", "Basic export", "API access"]}
            />
            <PricingCard
              tier="Professional"
              price="$199"
              description="For small firms and startups"
              features={["10,000 searches/month", "AI idea generation", "White space analysis", "50 watchlist items", "Priority support"]}
              highlighted
            />
            <PricingCard
              tier="Enterprise"
              price="$799"
              description="For corporate IP teams"
              features={["Unlimited searches", "Custom integrations", "Unlimited watchlist", "Team collaboration", "Dedicated support"]}
            />
          </div>
        </div>
      </section>

      {/* Coming Soon Section */}
      <section className="bg-gradient-to-br from-purple-900 via-indigo-900 to-purple-800 py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-3xl text-center">
            <span className="inline-flex items-center rounded-full bg-white/10 px-4 py-1.5 text-sm font-medium text-purple-200 mb-6">
              Coming Soon
            </span>
            <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
              Voice Patent Research
            </h2>
            <p className="mt-4 text-lg text-purple-200">
              Search, analyze, and explore patents with natural voice conversation. Powered by PersonaPlex full duplex AI.
            </p>
          </div>

          <div className="mx-auto mt-12 grid max-w-4xl grid-cols-1 gap-8 md:grid-cols-2">
            <div className="rounded-xl bg-white/5 border border-white/10 p-6">
              <h3 className="text-lg font-semibold text-purple-300 mb-4">Current Experience</h3>
              <ul className="space-y-2 text-sm text-purple-200/70">
                <li>• Type search queries manually</li>
                <li>• Click through results one by one</li>
                <li>• Read patent abstracts on screen</li>
                <li>• Type notes separately</li>
              </ul>
            </div>
            <div className="rounded-xl bg-purple-500/20 border border-purple-400/30 p-6">
              <h3 className="text-lg font-semibold text-purple-300 mb-4">With PersonaPlex</h3>
              <div className="space-y-3 text-sm">
                <div className="bg-black/20 rounded-lg px-3 py-2">
                  <span className="text-purple-300">You:</span>{" "}
                  <span className="text-white/80">"Show EV battery patents expiring soon"</span>
                </div>
                <div className="bg-purple-600/30 rounded-lg px-3 py-2">
                  <span className="text-purple-300">PersonaPlex:</span>{" "}
                  <span className="text-white/90">"Found 142 patents. Top one is from Tesla..."</span>
                </div>
                <div className="bg-black/20 rounded-lg px-3 py-2">
                  <span className="text-purple-300">You:</span>{" "}
                  <span className="text-white/80">"What's the white space here?"</span>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-12 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl mx-auto text-center">
            <div className="p-4">
              <p className="text-2xl font-bold text-purple-300">&lt;500ms</p>
              <p className="text-xs text-purple-200/70">Response Time</p>
            </div>
            <div className="p-4">
              <p className="text-2xl font-bold text-purple-300">Full Duplex</p>
              <p className="text-xs text-purple-200/70">Natural Conversation</p>
            </div>
            <div className="p-4">
              <p className="text-2xl font-bold text-purple-300">100%</p>
              <p className="text-xs text-purple-200/70">Local Processing</p>
            </div>
            <div className="p-4">
              <p className="text-2xl font-bold text-purple-300">Hands-Free</p>
              <p className="text-xs text-purple-200/70">Voice Control</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-primary-600 py-16">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h2 className="text-3xl font-bold text-white">Ready to discover patent opportunities?</h2>
            <p className="mt-4 text-lg text-primary-100">
              Start searching now — no credit card required.
            </p>
            <div className="mt-8 flex justify-center gap-4">
              <Link
                to="/search"
                className="rounded-lg bg-white px-6 py-3 text-base font-semibold text-primary-600 shadow-sm hover:bg-primary-50 transition-colors"
              >
                Get Started Free
              </Link>
              <Link
                to="/dashboard"
                className="rounded-lg border border-primary-300 px-6 py-3 text-base font-semibold text-white hover:bg-primary-500 transition-colors"
              >
                Explore Dashboard
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-white py-12">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center gap-2">
                <div className="h-6 w-6 rounded bg-primary-600 flex items-center justify-center">
                  <Zap className="h-4 w-4 text-white" />
                </div>
                <span className="text-sm font-semibold text-gray-900">Patent Intelligence</span>
              </div>
              <p className="mt-4 text-sm text-gray-500">
                AI-powered patent intelligence for innovators, researchers, and IP professionals.
              </p>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-gray-900">Product</h4>
              <ul className="mt-4 space-y-2">
                <li><Link to="/search" className="text-sm text-gray-500 hover:text-gray-900">Search</Link></li>
                <li><Link to="/expiration" className="text-sm text-gray-500 hover:text-gray-900">Expiration Tracker</Link></li>
                <li><Link to="/whitespace" className="text-sm text-gray-500 hover:text-gray-900">White Space</Link></li>
                <li><Link to="/ideas" className="text-sm text-gray-500 hover:text-gray-900">AI Ideas</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-gray-900">Analysis</h4>
              <ul className="mt-4 space-y-2">
                <li><Link to="/trends" className="text-sm text-gray-500 hover:text-gray-900">Trends</Link></li>
                <li><Link to="/similarity" className="text-sm text-gray-500 hover:text-gray-900">Similarity</Link></li>
                <li><Link to="/watchlist" className="text-sm text-gray-500 hover:text-gray-900">Watchlist</Link></li>
                <li><Link to="/dashboard" className="text-sm text-gray-500 hover:text-gray-900">Dashboard</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-gray-900">Resources</h4>
              <ul className="mt-4 space-y-2">
                <li><a href="/api/docs" className="text-sm text-gray-500 hover:text-gray-900">API Docs</a></li>
                <li><a href="https://github.com/dmhernandez2525/patent-intelligence" className="text-sm text-gray-500 hover:text-gray-900">GitHub</a></li>
              </ul>
            </div>
          </div>
          <div className="mt-12 border-t border-gray-200 pt-8">
            <p className="text-center text-sm text-gray-500">
              Built with React, FastAPI, PostgreSQL, and AI. Patent Intelligence Platform.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}

function FeatureCard({ icon, title, description, link }: { icon: React.ReactNode; title: string; description: string; link: string }) {
  return (
    <Link to={link} className="group rounded-xl border border-gray-200 bg-white p-6 shadow-sm hover:shadow-md hover:border-primary-200 transition-all">
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-100 text-primary-600 group-hover:bg-primary-600 group-hover:text-white transition-colors">
        {icon}
      </div>
      <h3 className="mt-4 text-lg font-semibold text-gray-900 group-hover:text-primary-600">{title}</h3>
      <p className="mt-2 text-sm text-gray-600">{description}</p>
    </Link>
  )
}

function StepCard({ number, title, description }: { number: string; title: string; description: string }) {
  return (
    <div className="text-center">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary-600 text-white text-lg font-bold">
        {number}
      </div>
      <h3 className="mt-4 text-lg font-semibold text-gray-900">{title}</h3>
      <p className="mt-2 text-sm text-gray-600">{description}</p>
    </div>
  )
}

function StatItem({ value, label, icon }: { value: string; label: string; icon: React.ReactNode }) {
  return (
    <div className="text-center">
      <div className="flex justify-center text-primary-600 mb-2">{icon}</div>
      <p className="text-3xl font-bold text-gray-900">{value}</p>
      <p className="mt-1 text-sm text-gray-600">{label}</p>
    </div>
  )
}

function PricingCard({
  tier,
  price,
  description,
  features,
  highlighted = false,
}: {
  tier: string
  price: string
  description: string
  features: string[]
  highlighted?: boolean
}) {
  return (
    <div
      className={`rounded-xl border p-6 ${
        highlighted
          ? 'border-primary-600 bg-primary-50 shadow-lg ring-1 ring-primary-600'
          : 'border-gray-200 bg-white shadow-sm'
      }`}
    >
      {highlighted && (
        <span className="inline-block rounded-full bg-primary-600 px-3 py-1 text-xs font-semibold text-white mb-4">
          Most Popular
        </span>
      )}
      <h3 className="text-lg font-semibold text-gray-900">{tier}</h3>
      <p className="mt-1 text-sm text-gray-600">{description}</p>
      <p className="mt-4">
        <span className="text-3xl font-bold text-gray-900">{price}</span>
        <span className="text-sm text-gray-600">/month</span>
      </p>
      <ul className="mt-6 space-y-3">
        {features.map((feature) => (
          <li key={feature} className="flex items-center gap-2 text-sm text-gray-700">
            <svg className="h-4 w-4 text-primary-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            {feature}
          </li>
        ))}
      </ul>
      <Link
        to="/search"
        className={`mt-6 block w-full rounded-lg py-2 text-center text-sm font-semibold transition-colors ${
          highlighted
            ? 'bg-primary-600 text-white hover:bg-primary-700'
            : 'border border-gray-300 text-gray-700 hover:bg-gray-50'
        }`}
      >
        Get Started
      </Link>
    </div>
  )
}

export default Landing
