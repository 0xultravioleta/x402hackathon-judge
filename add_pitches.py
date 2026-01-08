#!/usr/bin/env python3
"""Add 1-sentence pitch to rankings.md and rankings.json"""

import json
import re

def generate_pitch(project: dict) -> str:
    """Generate a 1-sentence pitch from project data."""
    name = project.get('project_name', '')
    desc = project.get('description', '')
    use_case = project.get('x402', {}).get('use_case', '')
    creative = project.get('x402', {}).get('creative_elements', [])
    strengths = project.get('strengths', [])

    # Clean up description - take first sentence or first 100 chars
    desc = desc.replace('\n', ' ').strip()

    # Build pitch based on project characteristics
    pitches = {
        'x402r': "Escrow-based refund system for AI payments - use it to get your money back if an API fails or returns bad data.",
        'Oops!402': "X402 payment gateway for ChatGPT and Claude - use it to let your AI agent pay for premium APIs with budget controls.",
        'Synapse': "Full infrastructure stack for AI agents - use it to give your agent a wallet, credit score, insurance, and dispute resolution.",
        'Pincher': "AI-powered carpooling with crypto payments - use it to share rides and split costs automatically via x402.",
        'Slophouse Cinema': "AI-generated movie theater with pay-per-view - use it to watch endless unique short films for micropayments.",
        'x402energy': "Energy trading marketplace for AI agents - use it to buy/sell renewable energy credits with automated payments.",
        'OpenFacilitator': "Open-source x402 payment facilitator - use it to add crypto payments to any API in minutes.",
        'Voiceswap': "AI voice cloning with x402 payments - use it to generate custom voiceovers and pay per generation.",
        'push': "Privacy-focused x402 payment relay - use it to make anonymous micropayments without revealing your wallet.",
        'Agent Trust Gateway': "Trust scoring for AI agent transactions - use it to verify agent reputation before accepting payments.",
        'x402-AI': "AI assistant with built-in payments - use it to let your chatbot pay for external services on your behalf.",
        'x402AI Assistant': "Personal AI that handles payments - use it to automate subscriptions and one-time purchases.",
        'Ora402': "Oracle service with x402 micropayments - use it to get real-time data feeds and pay only for what you query.",
        'RekonGG': "Gaming rewards platform with x402 - use it to earn crypto for achievements and spend it on in-game items.",
        'LinkSignX402': "Document signing with payment verification - use it to require payment before releasing signed contracts.",
        'x402-escrow': "Smart contract escrow for x402 - use it to hold payments until delivery is confirmed.",
        'xByte': "Data marketplace with micropayments - use it to buy/sell datasets with per-byte pricing.",
        'Vega Protocol': "DeFi derivatives with x402 integration - use it to trade options and pay fees via HTTP 402.",
        'x402 Swarm': "Distributed agent network with payments - use it to coordinate multiple AI agents sharing costs.",
        'x402-exec': "On-chain contract execution for agents - use it to let AI trigger smart contracts with payment.",
        'MicroAi-PayGate': "Payment gateway for AI microservices - use it to monetize your ML models with per-request pricing.",
        'Grantees': "Grant distribution with milestone payments - use it to release funds as project goals are met.",
        'Polymarket AI Agent': "Prediction market bot with x402 - use it to automate bets on Polymarket with spending limits.",
        'yoda.gg': "AI trading signals marketplace - use it to subscribe to alpha and pay per profitable signal.",
        'yoda.fun': "Social trading with x402 tips - use it to tip traders for good calls via micropayments.",
        'x402 Economic Load Balancer': "Cost-optimized API routing - use it to automatically pick the cheapest provider for each request.",
        'nanoPay': "Nano-scale payment infrastructure - use it to process payments as small as fractions of a cent.",
        'Bloom Protocol - Bloom Mission Bot': "Task completion with bounty payments - use it to pay agents for completing missions.",
        'x402 Proxy': "Payment proxy for legacy APIs - use it to add x402 to services that don't support it natively.",
        'X402 Paywall Builder': "No-code paywall creator - use it to monetize any content with drag-and-drop payment gates.",
        'everybid': "Auction platform with x402 deposits - use it to run auctions where bidders pay via HTTP 402.",
        'Nexus Protocol': "Cross-chain payment routing - use it to pay in any token and settle in the merchant's preferred currency.",
        'PredictOS - Prediction Market Intelligence': "AI predictions with paid confidence scores - use it to get probability estimates and pay more for higher accuracy.",
        'Cumulus': "Cloud compute marketplace - use it to rent GPU time and pay per second of usage.",
        'x402 Paywall': "Simple content paywall - use it to put articles behind a one-click micropayment.",
        'x402 answer book': "Q&A platform with paid answers - use it to charge for expert responses.",
        'WebAuthn x 402': "Hardware key authentication for payments - use it to approve x402 transactions with YubiKey.",
        'Fortuner': "Fortune telling AI with payments - use it to get personalized predictions for small fees.",
        'Turnstile Pay': "RaidGuild's x402 facilitator - use it to process payments for DAO services.",
        'Agentokratia Marketplace': "Marketplace for AI agent services - use it to hire agents and pay for task completion.",
        'Attentium': "Attention marketplace - use it to pay people for focused engagement with your content.",
        'x402 Kalshi Context Provider': "Kalshi data with x402 access - use it to get prediction market data via paid API.",
        'Brolli by Optilex': "Browser extension for x402 - use it to seamlessly pay for content as you browse.",
        'DNS402': "DNS with payment requirements - use it to gate domain resolution behind micropayments.",
        'DSX Engine': "Dataspace connector with payments - use it to share data between organizations with automatic billing.",
        'Miye': "Token swap agent - use it to automate DEX trades with payment for execution.",
        'PPS - Pay per second video streaming': "Video streaming with per-second billing - use it to watch content and pay only for time viewed.",
        'Autoincentive Weather Forecast': "Weather data with micropayments - use it to get forecasts and pay per location queried.",
        'medicProof': "Medical record verification - use it to share health data with payment for access.",
        'VELO': "Multi-chain velocity payments - use it to stream payments across different blockchains.",
        'MBCompass': "Navigation with paid premium features - use it to unlock advanced routing for micropayments.",
        'NodusAI': "Prediction oracle for AI agents - use it to get market forecasts with x402 billing.",
    }

    # Return custom pitch if available, otherwise generate generic one
    if name in pitches:
        return pitches[name]

    # Generic pitch based on description
    if desc:
        # Extract first meaningful sentence
        first_sentence = desc.split('.')[0].strip()
        if len(first_sentence) > 20:
            return f"{first_sentence} - use it to integrate x402 payments into your workflow."

    return f"X402-powered {name.lower()} - use it to add crypto micropayments to your project."


def update_rankings_json(json_path: str) -> dict:
    """Add pitch field to rankings.json and return data."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for project in data.get('rankings', []):
        project['pitch'] = generate_pitch(project)

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return data


def update_rankings_md(md_path: str, pitches: dict):
    """Add Pitch column to rankings.md."""
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    new_lines = []

    for line in lines:
        # Update header
        if '| Rank | Project | Video |' in line:
            line = line.rstrip(' |') + ' Pitch |'
            new_lines.append(line)
            continue

        # Update separator
        if line.startswith('|---') and 'Video' in new_lines[-1] if new_lines else False:
            line = line.rstrip(' |') + '-------|'
            new_lines.append(line)
            continue

        # Update data rows
        if line.startswith('|') and '| [' in line:
            # Extract project name
            match = re.search(r'\[([^\]]+)\]', line)
            if match:
                project_name = match.group(1)
                pitch = pitches.get(project_name, '-')
                line = line.rstrip(' |') + f' {pitch} |'

        new_lines.append(line)

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))


def main():
    json_path = '/mnt/z/ultravioleta/dao/hackathon-judge/results/rankings.json'
    md_path = '/mnt/z/ultravioleta/dao/hackathon-judge/results/rankings.md'

    print("Updating rankings.json with pitches...")
    data = update_rankings_json(json_path)

    # Build pitch lookup
    pitches = {}
    for project in data.get('rankings', []):
        pitches[project['project_name']] = project.get('pitch', '-')

    print(f"  Generated {len(pitches)} pitches")

    print("Updating rankings.md...")
    update_rankings_md(md_path, pitches)

    print("Done!")

    # Show sample
    print("\nSample pitches:")
    for name in list(pitches.keys())[:5]:
        print(f"  {name}: {pitches[name][:60]}...")


if __name__ == '__main__':
    main()
