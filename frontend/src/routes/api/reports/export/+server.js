import { env } from '$env/dynamic/public';

export async function GET({ cookies, url, request }) {
  const token = cookies.get('jwt_access');
  if (!token) return new Response('Please sign in.', { status: 401 });
  const params = new URLSearchParams(url.searchParams);
  params.set('download', 'csv');
  params.delete('page');
  const response = await fetch(`${env.PUBLIC_DJANGO_API_URL}/api/reports/crm/?${params}`, {
    headers: { Authorization: `Bearer ${token}` },
    signal: request.signal
  });
  if (!response.ok)
    return new Response(
      'The report could not be exported. Check your permissions and date range.',
      { status: response.status }
    );
  return new Response(response.body, {
    headers: {
      'Content-Type': 'text/csv; charset=utf-8',
      'Content-Disposition':
        response.headers.get('Content-Disposition') || 'attachment; filename="report.csv"',
      'Cache-Control': 'private, no-store'
    }
  });
}
