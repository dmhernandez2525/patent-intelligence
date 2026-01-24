import { Link } from 'react-router-dom'
import { Search, Clock, Lightbulb, TrendingUp, Shield, Zap } from 'lucide-react'

function Landing() {
  return (
    <div className="min-h-screen">
      {/* Navigation */}
      <nav className="border-b border-gray-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-primary-600 flex items-center justify-center">
                <Zap className="h-5 w-5 text-white" />
              </div>
              <span className="text-xl font-bold text-gray-900">Patent Intelligence</span>
            </div>
            <div className="flex items-center gap-4">
              <Link to="/dashboard" className="text-sm font-medium text-gray-600 hover:text-gray-900">
                Dashboard
              </Link>
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
            <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-6xl">
              Discover What's Expiring, What's Missing, and What's Next
            </h1>
            <p className="mt-6 text-lg leading-8 text-gray-600">
              AI-powered patent intelligence for innovators. Search 200M+ patents globally,
              track expirations, find white space opportunities, and generate invention ideas
              — at a fraction of enterprise pricing.
            </p>
            <div className="mt-10 flex items-center justify-center gap-4">
              <Link
                to="/search"
                className="rounded-lg bg-primary-600 px-6 py-3 text-base font-semibold text-white shadow-sm hover:bg-primary-700 transition-colors"
              >
                Start Searching
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
      </section>

      {/* Features Grid */}
      <section className="py-20 sm:py-28">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
              Patent Intelligence That Works For You
            </h2>
            <p className="mt-4 text-lg text-gray-600">
              Comprehensive tools for patent search, analysis, and opportunity discovery.
            </p>
          </div>
          <div className="mx-auto mt-16 grid max-w-5xl grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
            <FeatureCard
              icon={<Search className="h-6 w-6" />}
              title="Semantic Search"
              description="AI-powered patent search using PatentSBERTa embeddings. Find relevant patents by meaning, not just keywords."
            />
            <FeatureCard
              icon={<Clock className="h-6 w-6" />}
              title="Expiration Tracking"
              description="Real-time monitoring of patent expirations, maintenance fees, and lapsed patents. Never miss an opportunity."
            />
            <FeatureCard
              icon={<Lightbulb className="h-6 w-6" />}
              title="Idea Generation"
              description="LLM-powered invention suggestions based on expiring patents, technology gaps, and patent combinations."
            />
            <FeatureCard
              icon={<TrendingUp className="h-6 w-6" />}
              title="Trend Analysis"
              description="Technology trajectory mapping, CPC-based trends, and citation network analysis for strategic planning."
            />
            <FeatureCard
              icon={<Shield className="h-6 w-6" />}
              title="Prior Art Discovery"
              description="Vector-based similarity search for prior art candidates. Understand the landscape before filing."
            />
            <FeatureCard
              icon={<Zap className="h-6 w-6" />}
              title="White Space Analysis"
              description="Identify gaps in patent coverage and innovation opportunities that competitors have missed."
            />
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="border-y border-gray-200 bg-gray-50 py-16">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 gap-8 sm:grid-cols-4">
            <StatItem value="200M+" label="Global Patents" />
            <StatItem value="170+" label="Jurisdictions" />
            <StatItem value="50%" label="Patents Lapse" />
            <StatItem value="$49/mo" label="Starting Price" />
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section className="py-20">
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
              features={["1,000 searches/month", "Expiration tracking", "Basic export (10K)", "API access"]}
            />
            <PricingCard
              tier="Professional"
              price="$199"
              description="For small firms and startups"
              features={["10,000 searches/month", "AI idea generation", "White space analysis", "Priority support", "Export (100K)"]}
              highlighted
            />
            <PricingCard
              tier="Enterprise"
              price="$799"
              description="For corporate IP teams"
              features={["Unlimited searches", "Custom integrations", "Team collaboration", "Dedicated support", "Unlimited export"]}
            />
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-white py-12">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="h-6 w-6 rounded bg-primary-600 flex items-center justify-center">
                <Zap className="h-4 w-4 text-white" />
              </div>
              <span className="text-sm font-semibold text-gray-900">Patent Intelligence</span>
            </div>
            <p className="text-sm text-gray-500">
              Patent intelligence that doesn't require a patent lawyer's budget.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-100 text-primary-600">
        {icon}
      </div>
      <h3 className="mt-4 text-lg font-semibold text-gray-900">{title}</h3>
      <p className="mt-2 text-sm text-gray-600">{description}</p>
    </div>
  )
}

function StatItem({ value, label }: { value: string; label: string }) {
  return (
    <div className="text-center">
      <p className="text-3xl font-bold text-primary-600">{value}</p>
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
