import { NextResponse } from 'next/server';

const BACKEND_API_URL = process.env.BACKEND_API_URL || 'http://backend:8000/api/v1';

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_API_URL}/health`, {
      method: 'GET',
    });

    if (!response.ok) {
      return NextResponse.json(
        { status: 'unhealthy', error: 'Backend is not responding' },
        { status: 503 }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Health check error:', error);
    return NextResponse.json(
      { status: 'unhealthy', error: 'Failed to connect to backend' },
      { status: 503 }
    );
  }
}
