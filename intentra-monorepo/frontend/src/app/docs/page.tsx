import React from 'react';
import Link from 'next/link';
import { BookOpen, ShieldCheck, Zap, Bot, ArrowRight } from 'lucide-react';
import { PrimaryButton } from '@/components/ui/PrimaryButton';

export default function DocsPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 selection:bg-blue-200 dark:selection:bg-blue-900 selection:text-blue-900 dark:selection:text-blue-100 pb-20">
      
      {/* Navigation */}
      <nav className="sticky top-0 z-50 w-full backdrop-blur-md bg-white/70 dark:bg-gray-950/70 border-b border-gray-200 dark:border-gray-800 transition-colors duration-300">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
              <Bot className="w-8 h-8 text-blue-600 dark:text-blue-500" />
              <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600 dark:from-blue-400 dark:to-indigo-400">
                Intentra
              </span>
            </Link>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/dashboard">
              <PrimaryButton variant="secondary" className="hidden sm:flex">Dashboard</PrimaryButton>
            </Link>
            <Link href="/">
              <PrimaryButton className="rounded-full bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-500/20">
                Launch App
              </PrimaryButton>
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <div className="relative overflow-hidden pt-16 pb-24 lg:pt-32 lg:pb-40 border-b border-gray-200 dark:border-gray-800">
        <div className="absolute inset-0 bg-grid-slate-100 dark:bg-grid-slate-900/[0.04] bg-[bottom_1px_center] [mask-image:linear-gradient(to_bottom,transparent,black)]"></div>
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-sm font-medium mb-8">
            <BookOpen className="w-4 h-4" />
            Product Documentation
          </div>
          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight mb-8">
            AI-Driven Escrow on <br className="hidden sm:block" />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600">Arc Testnet</span>
          </h1>
          <p className="max-w-2xl mx-auto text-xl text-gray-600 dark:text-gray-400 mb-10 leading-relaxed">
            Intentra is a decentralized platform that matches your service intents with providers, secures payments on the blockchain, and uses autonomous AI agents to arbitrate disputes fairly and securely.
          </p>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        
        {/* Core Concepts */}
        <section className="mb-20">
          <h2 className="text-3xl font-bold mb-8 flex items-center gap-3">
            <Zap className="w-8 h-8 text-yellow-500" />
            Core Concepts
          </h2>
          <div className="grid sm:grid-cols-2 gap-6">
            <div className="p-6 bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 hover:shadow-md transition-shadow">
              <h3 className="text-xl font-semibold mb-3">Intent Matching</h3>
              <p className="text-gray-600 dark:text-gray-400 leading-relaxed">
                Users submit natural language &quot;Intents&quot; (e.g. &quot;I need a plumber tomorrow&quot;). Our AI engines instantly parse the requirements, budget, and location to find the perfect matched provider in our decentralized network.
              </p>
            </div>
            <div className="p-6 bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 hover:shadow-md transition-shadow">
              <h3 className="text-xl font-semibold mb-3">Immutable Escrow</h3>
              <p className="text-gray-600 dark:text-gray-400 leading-relaxed">
                Funds are secured on the Arc Testnet using a trustless smart contract. Payments are locked in escrow and can only be released upon mutual agreement or an authoritative AI ruling.
              </p>
            </div>
            <div className="p-6 bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 hover:shadow-md transition-shadow">
              <h3 className="text-xl font-semibold mb-3">EIP-712 Signatures</h3>
              <p className="text-gray-600 dark:text-gray-400 leading-relaxed">
                Intentra utilizes gasless EIP-712 signature standards to execute intent mandates and resolution signatures, ensuring maximum security and a seamless Web2-like user experience.
              </p>
            </div>
            <div className="p-6 bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 hover:shadow-md transition-shadow">
              <h3 className="text-xl font-semibold mb-3">AI Arbitration</h3>
              <p className="text-gray-600 dark:text-gray-400 leading-relaxed">
                Disputes are settled instantly by an unbiased AI Arbitrator trained on service industry standards. It reviews photographic evidence and conversation history to authorize fair fund splits on-chain.
              </p>
            </div>
          </div>
        </section>

        {/* How it Works */}
        <section className="mb-20">
          <h2 className="text-3xl font-bold mb-8 flex items-center gap-3">
            <ShieldCheck className="w-8 h-8 text-green-500" />
            How the Protocol Works
          </h2>
          <div className="space-y-8">
            <div className="flex gap-4">
              <div className="flex flex-col items-center">
                <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold">1</div>
                <div className="w-0.5 h-full bg-gray-200 dark:bg-gray-800 my-2"></div>
              </div>
              <div className="pb-8">
                <h3 className="text-xl font-semibold mb-2">Intent Creation</h3>
                <p className="text-gray-600 dark:text-gray-400">The user submits a natural language request. Our NVIDIA-powered LLMs parse the intent into a strict JSON schema, locking in the scope of work and budget parameters.</p>
              </div>
            </div>
            <div className="flex gap-4">
              <div className="flex flex-col items-center">
                <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold">2</div>
                <div className="w-0.5 h-full bg-gray-200 dark:bg-gray-800 my-2"></div>
              </div>
              <div className="pb-8">
                <h3 className="text-xl font-semibold mb-2">Smart Contract Funding</h3>
                <p className="text-gray-600 dark:text-gray-400">The user signs a transaction authorizing the transfer of USDC into the `IntentraEscrow.sol` smart contract deployed on Arc Testnet, binding the parsed intent data to the on-chain agreement.</p>
              </div>
            </div>
            <div className="flex gap-4">
              <div className="flex flex-col items-center">
                <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold">3</div>
                <div className="w-0.5 h-full bg-gray-200 dark:bg-gray-800 my-2"></div>
              </div>
              <div className="pb-8">
                <h3 className="text-xl font-semibold mb-2">Service Delivery & Dispute (Optional)</h3>
                <p className="text-gray-600 dark:text-gray-400">The provider delivers the service. If a disagreement arises, either party can upload photographic evidence and initiate a dispute through the platform UI.</p>
              </div>
            </div>
            <div className="flex gap-4">
              <div className="flex flex-col items-center">
                <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold">4</div>
              </div>
              <div>
                <h3 className="text-xl font-semibold mb-2">Resolution Execution</h3>
                <p className="text-gray-600 dark:text-gray-400">The AI Arbitrator reviews evidence and renders a binding percentage split. The backend dynamically generates an EIP-712 payload representing the split, which the user signs. The backend then executes the smart contract release, natively distributing funds back to the user and provider wallets.</p>
              </div>
            </div>
          </div>
        </section>
        
        {/* Call to Action */}
        <div className="mt-12 p-8 bg-blue-600 rounded-3xl text-white text-center shadow-xl shadow-blue-500/20">
          <h2 className="text-2xl font-bold mb-4">Ready to experience the future of service agreements?</h2>
          <p className="text-blue-100 mb-8 max-w-lg mx-auto">Try our testnet demo today and see how AI and Web3 combine to create trustless, frictionless commerce.</p>
          <Link href="/">
            <PrimaryButton variant="secondary" className="rounded-full text-blue-600 font-semibold px-8 hover:bg-white transition-colors">
              Open App <ArrowRight className="w-4 h-4 ml-2" />
            </PrimaryButton>
          </Link>
        </div>

      </div>
    </div>
  );
}
