// src/components/DataTable.jsx
export default function DataTable({ data }) {
    if (!data || !data.data || data.data.length === 0) return null;

    const headers = Object.keys(data.data[0]);

    return (
        <div className="table-container">
            <table>
                <thead>
                    <tr>
                        {headers.map((header) => (
                            <th key={header}>{header}</th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {data.data.map((row, i) => (
                        <tr key={i}>
                            {headers.map((header) => (
                                <td key={header}>{row[header]}</td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
