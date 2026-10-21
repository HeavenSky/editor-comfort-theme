<?php
namespace App\Http;

use Illuminate\Support\Facades\DB;

class UserController extends Controller
{
    public function show(int $id): array
    {
        $user = DB::table('users')->where('id', $id)->first();
        if ($user === null) {
            throw new \RuntimeException("user {$id} not found");
        }
        return ['name' => $user->name, 'active' => true, 'score' => 3.5];
    }
}
