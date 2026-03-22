using Dapper;
using Microsoft.Data.SqlClient;
using Microsoft.Extensions.Options;
using papermast.Entities.Options;

namespace papermast.Data.Access
{
    public class BaseAccess
    {
        protected readonly string _connectionString;


        public BaseAccess(IOptions<ConnectionStrings> options)
        {
            _connectionString = options.Value.Default;
        }

        public async Task<IEnumerable<T>> QueryAll<T>(string query, DynamicParameters parameters)
        {
            using( var connection = new SqlConnection(_connectionString))
            {
                await connection.OpenAsync();
                return await connection.QueryAsync<T>(query, parameters);
            }
        }

        public async Task<T?> QuerySingle<T>(string query, DynamicParameters parameters)
        {
            using (var connection = new SqlConnection(_connectionString))
            {
                await connection.OpenAsync();
                return await connection.QueryFirstOrDefaultAsync<T>(query, parameters);
            }
        }
    }
}
